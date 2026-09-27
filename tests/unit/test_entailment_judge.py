import json
import unittest

from src.qa.entailment_judge import LLMEntailmentJudge


class _FakeCompletions:
    def __init__(self):
        self.calls = 0

    def create(self, **_kwargs):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("temporary failure")
        message = type(
            "Message",
            (),
            {
                "content": json.dumps(
                    {
                        "label": "entailed",
                        "score": 0.95,
                        "matched_quote": "improved motor function",
                        "reason": "Direct support.",
                    }
                )
            },
        )()
        choice = type("Choice", (), {"message": message})()
        return type("Response", (), {"choices": [choice]})()


class EntailmentJudgeTest(unittest.TestCase):
    def test_transient_failure_is_retried_and_structured_result_is_returned(self):
        completions = _FakeCompletions()
        client = type(
            "Client",
            (),
            {"chat": type("Chat", (), {"completions": completions})()},
        )()
        judge = LLMEntailmentJudge(client, model="test", attempts=2, wait_seconds=0)

        result = judge(
            claim={"claim_id": "C001", "text": "Nusinersen improves motor function."},
            evidence_records=[
                {
                    "evidence_id": "T001",
                    "source_pmid": "1",
                    "evidence_text": "Nusinersen improved motor function.",
                }
            ],
        )

        self.assertEqual(result["label"], "entailed")
        self.assertEqual(completions.calls, 2)


if __name__ == "__main__":
    unittest.main()
