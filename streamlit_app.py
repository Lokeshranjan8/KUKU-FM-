from __future__ import annotations

import os
from urllib.parse import urlparse

import requests
import streamlit as st

API_URL = os.getenv("LEGAL_HELP_API_URL", "http://127.0.0.1:8000")
DISCLAIMER = (
    "NyayaSaathi gives general legal information, not legal advice. It can make mistakes "
    "and cannot predict what a court will decide. Check important information with a lawyer."
)


def _show_request_error(error: requests.RequestException, fallback: str) -> None:
    if isinstance(error, requests.HTTPError) and error.response is not None:
        try:
            detail = error.response.json().get("detail")
        except ValueError:
            detail = None
        st.error(detail or fallback)
        return
    st.error(fallback)


def _official_source(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host == "indiacode.nic.in" or host.endswith((".gov.in", ".nic.in"))


st.set_page_config(
    page_title="NyayaSaathi — understand your next step",
    page_icon="⚖️",
    layout="centered",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
    :root {
      --ink:#17382f; --muted:#63766d; --green:#24755c; --green-dark:#195e49;
      --pale:#edf5ef; --line:#e1e9e2; --surface:#fff;
    }
    .stApp {
      background:radial-gradient(ellipse at 50% 0%, #edf5ee 0, #f8faf7 44rem);
      color:var(--ink); font-family:'DM Sans',sans-serif;
    }
    .block-container { max-width:900px; padding:2.5rem 2rem 5rem; }
    header[data-testid="stHeader"] { background:transparent; }
    h1,h2,h3,h4 { font-family:'Manrope',sans-serif !important; color:var(--ink) !important; }
    h1 { font-size:clamp(2.15rem, 5vw, 3.2rem) !important; letter-spacing:-.045em; line-height:1.08 !important; }
    h2 { letter-spacing:-.025em; }
    .brand {
      display:inline-flex; align-items:center; padding:.48rem .78rem;
      border:1px solid #dbe8dd; border-radius:999px; background:#ffffffbb;
      color:var(--green-dark); font-size:.78rem; font-weight:700; letter-spacing:.08em;
    }
    .hero { padding:2.15rem 0 1.05rem; }
    .eyebrow { color:var(--green); font-size:.74rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase; }
    .lead { color:var(--muted); font-size:1.08rem; line-height:1.7; max-width:680px; margin-top:.75rem; }
    .note {
      background:#edf5ef; border:1px solid #d9e8dc; border-left:4px solid #68a786;
      border-radius:12px; padding:1rem 1.15rem; color:#40574a; font-size:.92rem; line-height:1.65;
      margin:.5rem 0 1.5rem;
    }
    .section-kicker {
      margin:0 0 .35rem; color:var(--green); font-size:.72rem;
      font-weight:700; letter-spacing:.12em; text-transform:uppercase;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
      border:1px solid var(--line); border-radius:18px; background:var(--surface);
      box-shadow:0 12px 34px #233c2b0b;
    }
    [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
      border-radius:11px; border-color:#dbe4dc; background:#fcfdfb;
      line-height:1.55; transition:border-color .15s, box-shadow .15s;
    }
    [data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
      border-color:#68a786; box-shadow:0 0 0 3px #68a78624;
    }
    [data-testid="stCheckbox"] { padding:.35rem 0; }
    [data-testid="stCheckbox"] label { color:#40574a; font-size:.9rem; line-height:1.5; }
    [data-testid="stExpander"] {
      border:1px solid var(--line); border-radius:12px; background:#fbfcfa;
      overflow:hidden;
    }
    [data-testid="stExpander"] summary { color:var(--ink); font-weight:600; }
    .stButton > button, [data-testid="stLinkButton"] a {
      border-radius:11px; min-height:44px; font-weight:700; transition:transform .15s, box-shadow .15s;
    }
    .stButton > button[kind="primary"] {
      border:0; background:var(--green); box-shadow:0 5px 14px #24755c28;
    }
    .stButton > button[kind="primary"]:hover {
      background:var(--green-dark); box-shadow:0 7px 18px #24755c38; transform:translateY(-1px);
    }
    [data-testid="stAlert"] { border-radius:12px; }
    [data-testid="stCaptionContainer"] { color:var(--muted); }
    hr { border-color:var(--line); margin:2rem 0; }
    footer { visibility:hidden; }
    @media (max-width:640px) {
      .block-container { padding:1.25rem 1rem 3rem; }
      .hero { padding:1.5rem 0 .8rem; }
      .lead { font-size:1rem; }
      .note { padding:.9rem 1rem; }
      [data-testid="stVerticalBlockBorderWrapper"] { border-radius:14px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="brand">⚖️ &nbsp; NYAYASAATHI</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Indian criminal-law help, in plain English</div>
      <h1 style="margin:.35rem 0">Tell us what happened.</h1>
      <p class="lead">Get a clear summary, questions to consider, practical options, and
      help understanding the next steps in the legal process.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="note">This is not a lawyer or emergency service. Avoid sharing names, '
    "addresses, phone numbers, or other identifying details. Your story is sent to the "
    "configured chat AI. A voice recording is sent to the configured transcription provider "
    "(Sarvam when enabled); the app does not save a case history.</div>",
    unsafe_allow_html=True,
)

with st.container(border=True):
    st.markdown('<div class="section-kicker">Start with the basics</div>', unsafe_allow_html=True)
    st.caption("A little context helps make the information more relevant.")
    location = st.text_input(
        "Where did this happen? (state or union territory)",
        placeholder="e.g. Maharashtra",
        max_chars=100,
    )
    consent = st.checkbox(
        "I understand my text or recording will be sent to the AI service configured for this app."
    )

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "transcribed_text" in st.session_state:
    st.session_state["case_input"] = st.session_state.pop("transcribed_text")
if st.session_state.pop("clear_case_input", False):
    st.session_state["case_input"] = ""

with st.container(border=True):
    st.markdown('<div class="section-kicker">Tell us what you need</div>', unsafe_allow_html=True)
    st.caption("Share only the details you are comfortable including. You can type or record your description.")
    with st.expander("Speak instead of typing"):
        audio = st.audio_input("Record a short description (English)")
        if st.button("Transcribe recording", disabled=audio is None or not consent):
            try:
                response = requests.post(
                    f"{API_URL}/api/transcribe",
                    data=audio.getvalue(),
                    headers={
                        "Content-Type": audio.type or "application/octet-stream",
                        "X-User-Consent": "true",
                        "X-Audio-Filename": audio.name or "recording.wav",
                    },
                    timeout=100,
                )
                response.raise_for_status()
                st.session_state["transcribed_text"] = response.json()["text"]
                st.rerun()
            except requests.RequestException as error:
                _show_request_error(
                    error,
                    "We could not transcribe this recording. Check the AI settings and try again.",
                )

    text = st.text_area(
        "What happened, or what would you like to ask next?",
        placeholder="Describe what happened in your own words. Include roughly when and where, what you have done so far, and what you want to understand.",
        height=170,
        max_chars=4000,
        key="case_input",
    )

    if st.button(
        "Help me understand my options →",
        type="primary",
        use_container_width=True,
        disabled=not consent or not text.strip(),
    ):
        messages = [*st.session_state["messages"], {"role": "user", "content": text.strip()}]
        st.session_state["analysis"] = None
        try:
            response = requests.post(
                f"{API_URL}/api/analyze",
                # the API accepts at most 20 messages of 4000 chars each, so send
                # the latest part of the chat and trim any very long AI reply
                json={
                    "location": location,
                    "messages": [
                        {"role": m["role"], "content": m["content"][:4000]}
                        for m in messages[-20:]
                    ],
                },
                timeout=100,
            )
            response.raise_for_status()
            analysis = response.json()
            st.session_state["messages"] = [
                *messages,
                {"role": "assistant", "content": analysis["response"]},
            ]
            st.session_state["analysis"] = analysis
            st.session_state["clear_case_input"] = True
            st.rerun()
        except requests.RequestException as error:
            _show_request_error(
                error,
                "We could not prepare an answer. Check the AI settings and try again.",
            )

analysis = st.session_state.get("analysis")
if analysis:
    st.divider()
    st.subheader("Your situation")
    st.caption(analysis["issue_type"])
    st.write(analysis["overview"])
    st.info(analysis["response"])

    if analysis["urgency"]:
        st.markdown("#### Safety and urgency")
        st.write(analysis["urgency"])

    if analysis["clarifying_questions"]:
        st.markdown("#### A few details that may matter")
        for question in analysis["clarifying_questions"]:
            st.markdown(f"- {question}")

    if analysis["possible_laws"]:
        st.markdown("#### Possible laws to check")
        st.caption(
            "These are AI-suggested possibilities, not verified legal advice. "
            "Check the act, section, date, and source with a lawyer."
        )
        for law in analysis["possible_laws"]:
            with st.container(border=True):
                st.markdown(f"**{law['act']} · {law['section']}**")
                st.write(law["relevance"])
                if law["caveat"]:
                    st.caption(law["caveat"])
                if law["source_url"].startswith("https://") and _official_source(
                    law["source_url"]
                ):
                    st.link_button("Check source", law["source_url"])
                else:
                    st.caption(
                        "No recognized official source link was provided; verify before relying on it."
                    )
    if analysis.get("dropped_citations"):
        st.caption(
            f"{analysis['dropped_citations']} AI-suggested law(s) were hidden because they were "
            "not found in NyayaSaathi's law references."
        )
    if analysis.get("sources"):
        with st.expander("Law references NyayaSaathi checked for this story"):
            st.caption(
                "These were picked from the app's law notes by matching your words. "
                "They are short summaries, not the official text."
            )
            for source in analysis["sources"]:
                st.markdown(
                    f"- **{source['act']} · {source['section']}**: {source['title']} "
                    f"([source]({source['source_url']}))"
                )

    if analysis["options"]:
        st.markdown("#### Practical options")
        for option in analysis["options"]:
            with st.container(border=True):
                st.markdown(f"**{option['title']}**")
                st.write(option["explanation"])
                st.caption(f"Possible first step: {option['first_step']}")

    if analysis["court_process"]:
        st.markdown("#### How the process may work")
        for index, step in enumerate(analysis["court_process"], start=1):
            st.markdown(f"{index}. {step}")

    st.markdown("#### Facts and evidence to consider")
    factors = analysis["case_factors"]
    if factors["supporting_facts"]:
        st.markdown("**Facts you shared that may be relevant**")
        for item in factors["supporting_facts"]:
            st.markdown(f"- {item}")
    if factors["missing_or_unclear"]:
        st.markdown("**Still unclear**")
        for item in factors["missing_or_unclear"]:
            st.markdown(f"- {item}")
    if factors["important_caveats"]:
        st.markdown("**Important limits**")
        for item in factors["important_caveats"]:
            st.markdown(f"- {item}")

    if analysis["evidence"]:
        for item in analysis["evidence"]:
            with st.container(border=True):
                st.markdown(f"**{item['item']}**")
                st.caption(item["why_it_may_help"])

    if analysis["lawyer_recommendation"]:
        st.markdown("#### Speaking with a lawyer")
        st.write(analysis["lawyer_recommendation"])
    st.markdown(
        "You can also check free legal-aid information with the "
        "[National Legal Services Authority (NALSA)](https://nalsa.gov.in/)."
    )
    st.caption(DISCLAIMER)

    with st.expander("Conversation so far"):
        for message in st.session_state["messages"]:
            st.markdown(f"**{'You' if message['role'] == 'user' else 'NyayaSaathi'}**")
            st.write(message["content"])

st.caption("If someone is in immediate danger, contact local emergency services now.")
