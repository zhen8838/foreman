import io
import runpy
import unittest
from pathlib import Path
from unittest.mock import patch


FOREMAN = Path(__file__).resolve().parents[1] / "bin" / "foreman"


class SubmitPromptTest(unittest.TestCase):
    def setUp(self) -> None:
        self.submit_prompt = runpy.run_path(str(FOREMAN))["submit_prompt"]
        self.calls = []

    def _send(self, result: dict) -> str:
        def fake_hc(*args, check=True):
            self.calls.append(args)
            return result

        stderr = io.StringIO()
        with patch.dict(self.submit_prompt.__globals__, {"hc": fake_hc}), \
                patch("sys.stderr", stderr):
            self.submit_prompt("x-rev", "-- line one\nline two")
        return stderr.getvalue()

    def test_text_goes_after_double_dash_with_newlines_kept(self) -> None:
        self._send({"started": True, "status": "idle", "turn": 3})
        self.assertEqual(self.calls, [("send", "--", "x-rev", "-- line one\nline two")])

    def test_started_turn_is_silent(self) -> None:
        self.assertEqual(self._send({"started": True, "status": "done", "turn": 3}), "")

    def test_busy_recipient_is_reported_as_unconfirmed(self) -> None:
        out = self._send({"started": False, "status": "working", "turn": 3})
        self.assertIn("most likely queued", out)

    def test_no_new_turn_points_at_the_input_box(self) -> None:
        out = self._send({"started": False, "status": "idle", "turn": 3})
        self.assertIn("stuck in the input box", out)

    def test_program_without_status_cannot_confirm(self) -> None:
        out = self._send({"started": None, "status": None, "turn": 0})
        self.assertIn("reports no status", out)

    def test_blocked_recipient_is_not_forced(self) -> None:
        with self.assertRaisesRegex(SystemExit, "blocked .* Nothing was sent"):
            self._send({"error": {"kind": "blocked", "message": "blocked"}, "exit": 9})
        self.assertNotIn("--force", self.calls[0])


if __name__ == "__main__":
    unittest.main()
