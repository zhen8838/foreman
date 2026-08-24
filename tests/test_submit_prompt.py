import runpy
import types
import unittest
from pathlib import Path
from unittest.mock import patch


FOREMAN = Path(__file__).resolve().parents[1] / "bin" / "foreman"


class SubmitPromptTest(unittest.TestCase):
    def test_enter_precedes_transition_check(self) -> None:
        namespace = runpy.run_path(str(FOREMAN))
        submit_prompt = namespace["submit_prompt"]
        calls = []
        states = iter([
            {"agent": {"agent_status": "idle", "state_change_seq": 10}},
            {"agent": {"agent_status": "working", "state_change_seq": 11}},
        ])

        def fake_herdr(*args):
            calls.append(args)
            return next(states) if args[:2] == ("agent", "get") else {}

        with patch.dict(submit_prompt.__globals__, {
            "herdr": fake_herdr,
            "time": types.SimpleNamespace(sleep=lambda _seconds: None),
        }):
            submit_prompt("w1:p1", "do the work", tries=1, settle_s=0)

        self.assertEqual(calls, [
            ("agent", "get", "w1:p1"),
            ("agent", "prompt", "w1:p1", "do the work"),
            ("agent", "send-keys", "w1:p1", "enter"),
            ("agent", "get", "w1:p1"),
        ])


if __name__ == "__main__":
    unittest.main()
