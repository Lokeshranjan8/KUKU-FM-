from __future__ import annotations

import json
import os
from typing import Any

import requests
from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError

from backend.rag import format_context, retrieve


class PossibleLaw(BaseModel):
    ref_id: str = ""
    act: str
    section: str
    relevance: str
    source_url: str = ""
    caveat: str = ""


class CaseOption(BaseModel):
    title: str
    explanation: str
    first_step: str


class EvidenceItem(BaseModel):
    item: str
    why_it_may_help: str


class CaseFactors(BaseModel):
    supporting_facts: list[str] = Field(default_factory=list)
    missing_or_unclear: list[str] = Field(default_factory=list)
    important_caveats: list[str] = Field(default_factory=list)


class SourceRef(BaseModel):
    id: str
    act: str
    section: str
    title: str
    source_url: str


class CaseAnalysis(BaseModel):
    overview: str
    issue_type: str
    clarifying_questions: list[str] = Field(default_factory=list)
    possible_laws: list[PossibleLaw] = Field(default_factory=list)
    options: list[CaseOption] = Field(default_factory=list)
    court_process: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    case_factors: CaseFactors
    urgency: str
    lawyer_recommendation: str
    response: str
    sources: list[SourceRef] = Field(default_factory=list)
    dropped_citations: int = 0


def _settings() -> tuple[str, str, str]:
    api_base_url = os.getenv("AI_API_BASE_URL", "").strip().rstrip("/")
    api_key = os.getenv("AI_API_KEY", "").strip()
    model = os.getenv("AI_MODEL", "").strip()
    if not api_base_url or not api_key or not model:
        raise HTTPException(
            status_code=503,
            detail=(
                "AI is not configured. Set AI_API_BASE_URL, AI_API_KEY, and AI_MODEL "
                "to an OpenAI-compatible chat-completions service."
            ),
        )
    return api_base_url, api_key, model


def _system_prompt(location: str, context: str = "") -> str:
    return f"""
You are NyayaSaathi, a careful legal information assistant for criminal matters in India.
Help people understand their situation in plain English. You are not a lawyer and must
not claim to represent anyone, decide guilt, promise an outcome, or give a win probability.
The user may be distressed. Be respectful, calm, and do not blame them.
If the issue is not criminal, say that this first version focuses on criminal matters and
avoid forcing the story into a criminal offence.

The user's stated location is: {location or "not provided"}.

Use only facts the user gave. Do not fill gaps with assumptions. Ask a small number of
specific clarifying questions when answers could change the options. Distinguish allegations
from established facts. Do not ask for full names, exact addresses, phone numbers, or other
unnecessary identifying details.

Explain practical options in India in accessible language, including what the police,
magistrate, and courts generally do only where relevant. Procedures can depend on the
offence, date, location, and facts. Do not tell the user to confront a suspected offender
or destroy, edit, or secretly obtain evidence.

REFERENCE LAWS (retrieved from the app's knowledge base for this story):
{context or "(nothing relevant was found)"}

You may mention a law or section ONLY if it appears in the reference list above. Put its
id (the text in square brackets) in "ref_id". Never invent a section number, case citation,
deadline, or source, and never cite a law that is not in the list. If none of the listed
laws clearly fit, leave possible_laws empty and say what needs verification. The list gives
the new law and its earlier equivalent; the new criminal laws apply to offences from
1 July 2024, so consider the incident date and do not silently assume one version. Any
suggested provision is a possibility to verify, not a legal conclusion.

Do not rate the case or give a percentage. Describe only potential supporting facts,
missing/unclear facts, and caveats. Explain that evidence is assessed in context and by
the proper authorities/court. If there may be immediate danger or a medical emergency,
say to seek immediate local emergency help and not wait for this app. When a lawyer may
be important or the user cannot afford one, mention the District/State Legal Services
Authority and https://nalsa.gov.in/ as a place to check legal-aid information. Do not
pretend to find or contact a lawyer.

Reply in English and return only a JSON object with this exact shape:
{{
  "overview": "short summary of the user's account, explicitly not a finding of fact",
  "issue_type": "plain language issue category",
  "clarifying_questions": ["question"],
  "possible_laws": [
    {{"ref_id":"id from the reference list","act":"Act name","section":"section","relevance":"why it may relate",
     "source_url":"official URL","caveat":"what must be verified"}}
  ],
  "options": [
    {{"title":"option","explanation":"plain language explanation","first_step":"practical next step"}}
  ],
  "court_process": ["relevant general process step"],
  "evidence": [
    {{"item":"record or evidence","why_it_may_help":"why to preserve it"}}
  ],
  "case_factors": {{
    "supporting_facts":["fact supplied by user"],
    "missing_or_unclear":["unknown detail"],
    "important_caveats":["limitation"]
  }},
  "urgency": "plain language urgency note",
  "lawyer_recommendation": "whether to seek local legal advice and why",
  "response": "direct, supportive answer to the user's latest message"
}}
""".strip()


def _ground_citations(analysis: CaseAnalysis, retrieved: list[dict]) -> CaseAnalysis:
    """Keep only laws that came from retrieval, and take act/section/link from our data."""
    by_id = {r["id"]: r for r in retrieved}
    kept = []
    for law in analysis.possible_laws:
        ref = by_id.get(law.ref_id.strip())
        if ref is None:
            continue
        kept.append(
            law.model_copy(
                update={"act": ref["act"], "section": ref["section"], "source_url": ref["source_url"]}
            )
        )
    analysis.dropped_citations = len(analysis.possible_laws) - len(kept)
    analysis.possible_laws = kept
    analysis.sources = [
        SourceRef(
            id=r["id"], act=r["act"], section=r["section"],
            title=r["title"], source_url=r["source_url"],
        )
        for r in retrieved
    ]
    return analysis


def analyze_case(messages: list[dict[str, str]], location: str) -> CaseAnalysis:
    api_base_url, api_key, model = _settings()
    # search with everything the user has said so far, so follow-up answers help retrieval
    query = " ".join(m["content"] for m in messages if m["role"] == "user")
    retrieved = retrieve(query)
    try:
        response = requests.post(
            f"{api_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": _system_prompt(location, format_context(retrieved))},
                    *messages,
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=90,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail="The AI service could not complete the request. Check its URL and settings, then try again.",
        ) from error

    try:
        content = response.json()["choices"][0]["message"]["content"]
        analysis = CaseAnalysis.model_validate(json.loads(content))
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValidationError) as error:
        raise HTTPException(
            status_code=502,
            detail="The AI service returned an unexpected response. Please try again.",
        ) from error
    return _ground_citations(analysis, retrieved)


def _transcribe_with_sarvam(
    audio: bytes,
    filename: str,
    content_type: str,
    api_key: str,
) -> str:
    model = os.getenv("SARVAM_TRANSCRIPTION_MODEL", "saarika:v2.5").strip()
    try:
        response = requests.post(
            "https://api.sarvam.ai/speech-to-text",
            headers={"api-subscription-key": api_key},
            data={"model": model, "language_code": "en-IN"},
            files={
                "file": (
                    filename or "recording.wav",
                    audio,
                    content_type or "application/octet-stream",
                )
            },
            timeout=90,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail="Sarvam could not transcribe the recording. Check its API key and transcription settings, then try again.",
        ) from error

    try:
        result = response.json()
        text = result.get("transcript") or result.get("text")
    except (AttributeError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=502,
            detail="Sarvam returned an unexpected transcription response.",
        ) from error

    if not isinstance(text, str) or not text.strip():
        raise HTTPException(status_code=502, detail="No speech was detected in the recording.")
    return text.strip()


def transcribe_audio(audio: bytes, filename: str, content_type: str) -> str:
    if not audio:
        raise HTTPException(status_code=400, detail="Choose a recording before transcribing.")

    if len(audio) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio must be smaller than 20 MB.")

    sarvam_api_key = os.getenv("SARVAM_API_KEY", "").strip()
    if sarvam_api_key:
        return _transcribe_with_sarvam(audio, filename, content_type, sarvam_api_key)

    api_base_url, api_key, _ = _settings()
    model = os.getenv("AI_TRANSCRIPTION_MODEL", "").strip()
    if not model:
        raise HTTPException(
            status_code=503,
            detail=(
                "Voice transcription is not configured. Set SARVAM_API_KEY, or set "
                "AI_TRANSCRIPTION_MODEL for your OpenAI-compatible provider."
            ),
        )

    try:
        response = requests.post(
            f"{api_base_url}/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            data={"model": model},
            files={
                "file": (
                    filename or "recording.wav",
                    audio,
                    content_type or "application/octet-stream",
                )
            },
            timeout=90,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise HTTPException(
            status_code=502,
            detail="The AI service could not transcribe the audio. Check its settings, then try again.",
        ) from error

    try:
        text = response.json()["text"]
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=502,
            detail="The transcription service returned an unexpected response.",
        ) from error
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(status_code=502, detail="No speech was detected in the recording.")
    return text.strip()
