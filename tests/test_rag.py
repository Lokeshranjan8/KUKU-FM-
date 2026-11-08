import json
import os
import unittest
from unittest.mock import Mock, patch

from backend.rag import get_index, retrieve
from backend.service import analyze_case


def _fake_llm_reply(possible_laws):
    body = {
        "overview": "o", "issue_type": "theft", "clarifying_questions": [],
        "possible_laws": possible_laws, "options": [], "court_process": [], "evidence": [],
        "case_factors": {"supporting_facts": [], "missing_or_unclear": [], "important_caveats": []},
        "urgency": "", "lawyer_recommendation": "", "response": "r",
    }
    response = Mock()
    response.json.return_value = {"choices": [{"message": {"content": json.dumps(body)}}]}
    return response


class RetrievalTests(unittest.TestCase):
    def test_theft_story_finds_theft_section(self):
        ids = [r["id"] for r in get_index().search("someone stole my phone in the bus")]
        self.assertIn("bns-303", ids)

    def test_always_includes_fir_and_legal_aid(self):
        ids = [r["id"] for r in retrieve("my neighbour slapped me")]
        self.assertIn("bnss-173", ids)
        self.assertIn("lsa-12", ids)

    def test_empty_query_returns_nothing(self):
        self.assertEqual(get_index().search("   "), [])


@patch.dict(os.environ, {"AI_API_BASE_URL": "http://x", "AI_API_KEY": "k", "AI_MODEL": "m"}, clear=True)
class GroundingTests(unittest.TestCase):
    @patch("backend.service.requests.post")
    def test_retrieved_laws_go_into_prompt(self, post):
        post.return_value = _fake_llm_reply([])
        analyze_case([{"role": "user", "content": "someone stole my phone"}], "Delhi")
        system_prompt = post.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertIn("[bns-303]", system_prompt)

    @patch("backend.service.requests.post")
    def test_made_up_citation_is_dropped_and_real_one_is_corrected(self, post):
        post.return_value = _fake_llm_reply([
            {"ref_id": "bns-303", "act": "wrong act", "section": "999", "relevance": "theft"},
            {"ref_id": "", "act": "Made Up Act", "section": "42", "relevance": "invented"},
        ])
        result = analyze_case([{"role": "user", "content": "someone stole my phone"}], "")

        self.assertEqual(len(result.possible_laws), 1)
        self.assertEqual(result.possible_laws[0].section, "303")
        self.assertEqual(result.possible_laws[0].act, "Bharatiya Nyaya Sanhita, 2023")
        self.assertEqual(result.dropped_citations, 1)
        self.assertTrue(result.sources)


if __name__ == "__main__":
    unittest.main()
