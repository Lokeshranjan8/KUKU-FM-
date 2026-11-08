import os
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException
from pydantic import ValidationError

from backend.service import CaseAnalysis, _system_prompt, transcribe_audio


class AnalysisContractTests(unittest.TestCase):
    def test_analysis_contract_accepts_an_open_ended_answer(self):
        answer = CaseAnalysis.model_validate(
            {
                "overview": "Summary of the user's account.",
                "issue_type": "Criminal complaint",
                "clarifying_questions": ["When did this happen?"],
                "possible_laws": [],
                "options": [],
                "court_process": [],
                "evidence": [],
                "case_factors": {
                    "supporting_facts": [],
                    "missing_or_unclear": ["Date"],
                    "important_caveats": [],
                },
                "urgency": "No immediate danger described.",
                "lawyer_recommendation": "Speak with a local lawyer for advice.",
                "response": "I can help you organize the next steps.",
            }
        )

        self.assertEqual(answer.issue_type, "Criminal complaint")
        self.assertEqual(answer.possible_laws, [])
        self.assertEqual(answer.case_factors.missing_or_unclear, ["Date"])

    def test_analysis_contract_rejects_missing_case_factors(self):
        with self.assertRaises(ValidationError):
            CaseAnalysis.model_validate(
                {
                    "overview": "Summary",
                    "issue_type": "Unknown",
                    "urgency": "",
                    "lawyer_recommendation": "",
                    "response": "",
                }
            )

    def test_prompt_requires_caution_and_no_win_score(self):
        prompt = _system_prompt("not provided")

        self.assertIn("Do not rate the case or give a percentage", prompt)
        self.assertIn("Never invent a section number", prompt)
        self.assertIn("https://nalsa.gov.in/", prompt)


class TranscriptionTests(unittest.TestCase):
    @patch.dict(
        os.environ,
        {"SARVAM_API_KEY": "test-key", "SARVAM_TRANSCRIPTION_MODEL": "saarika:v2.5"},
        clear=True,
    )
    @patch("backend.service.requests.post")
    def test_sarvam_transcription_uses_sarvam_and_returns_transcript(self, post):
        response = Mock()
        response.json.return_value = {"transcript": "Hello from a test recording"}
        post.return_value = response

        text = transcribe_audio(b"audio bytes", "sample.wav", "audio/wav")

        self.assertEqual(text, "Hello from a test recording")
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.sarvam.ai/speech-to-text")
        self.assertEqual(kwargs["headers"], {"api-subscription-key": "test-key"})
        self.assertEqual(
            kwargs["data"],
            {"model": "saarika:v2.5", "language_code": "en-IN"},
        )
        self.assertEqual(kwargs["files"]["file"][0:3], ("sample.wav", b"audio bytes", "audio/wav"))

    @patch.dict(os.environ, {"SARVAM_API_KEY": "test-key"}, clear=True)
    def test_transcription_rejects_empty_audio(self):
        with self.assertRaises(HTTPException) as raised:
            transcribe_audio(b"", "sample.wav", "audio/wav")

        self.assertEqual(raised.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
