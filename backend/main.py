from __future__ import annotations

from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from backend.service import CaseAnalysis, analyze_case, transcribe_audio

app = FastAPI(
    title="NyayaSaathi API",
    description="A cautious AI helper for understanding criminal-law options in India.",
    version="1.0.0",
)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class CaseRequest(BaseModel):
    location: str = Field(default="", max_length=100)
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze", response_model=CaseAnalysis)
def analyze(request: CaseRequest) -> CaseAnalysis:
    if request.messages[-1].role != "user":
        raise HTTPException(status_code=400, detail="The latest message must be from the user.")
    return analyze_case(
        [message.model_dump() for message in request.messages],
        request.location,
    )


@app.post("/api/transcribe")
async def transcribe(
    request: Request,
    consent: bool = Header(default=False, alias="X-User-Consent"),
    filename: str = Header(default="recording.wav", alias="X-Audio-Filename"),
) -> dict[str, str]:
    if not consent:
        raise HTTPException(
            status_code=400,
            detail="Consent is required before audio is sent to the configured AI service.",
        )
    audio = bytearray()
    async for chunk in request.stream():
        if len(audio) + len(chunk) > 20 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Audio must be smaller than 20 MB.")
        audio.extend(chunk)
    return {
        "text": transcribe_audio(
            bytes(audio),
            filename,
            request.headers.get("content-type", "application/octet-stream"),
        )
    }
