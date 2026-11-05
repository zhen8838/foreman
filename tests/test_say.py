import json
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


FOREMAN = Path(__file__).resolve().parents[1] / "bin" / "foreman"


class ResolveRecipientTest(unittest.TestCase):
    def setUp(self) -> None:
        self.resolve = runpy.run_path(str(FOREMAN))["resolve_recipient"]
        self.tmp = tempfile.TemporaryDirectory()
        self.jobs = Path(self.tmp.name)
        self.job = {"task": "x", "agents": {
            "impl": {"handle": "x-impl", "address": "t1b"},
            "review": {"handle": "x-rev", "address": "t1c"},
        }}
        (self.jobs / "x.json").write_text(json.dumps(self.job))
        self.known = {"t1b", "t1c", "t9"}

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _resolve(self, words: str, me=None):
        def fake_hc(cmd, *args, check=True):
            target = args[-1]
            return {"address": target} if target in self.known else {"error": {}, "exit": 3}

        with patch.dict(self.resolve.__globals__, {"hc": fake_hc, "JOBS": self.jobs}):
            return self.resolve(words.split(), me)

    def test_task_and_role_resolve_to_the_terminal_name(self) -> None:
        self.assertEqual(self._resolve("x.rev PASS"), ("x-rev", "x-rev = x.review", ["PASS"]))
        self.assertEqual(self._resolve("x-impl go")[0], "x-impl")
        self.assertEqual(self._resolve("x go")[0], "x-impl")

    def test_known_address_is_a_recipient_and_named_from_the_ledger(self) -> None:
        self.assertEqual(self._resolve("t1c hi"), ("t1c", "t1c = x.review", ["hi"]))
        self.assertEqual(self._resolve("t9 hi"), ("t9", "t9", ["hi"]))

    def test_word_shaped_like_an_address_stays_in_the_message(self) -> None:
        me = (self.job, "impl")
        self.assertEqual(self._resolve("the diff is ready", me),
                         ("x-rev", "x-rev = x.review", ["the", "diff", "is", "ready"]))

    def test_partner_is_the_default_inside_a_job(self) -> None:
        self.assertEqual(self._resolve("PASS", (self.job, "review"))[0], "x-impl")

    def test_outside_a_job_a_recipient_is_required(self) -> None:
        with self.assertRaisesRegex(SystemExit, "belongs to no job"):
            self._resolve("hello there")


if __name__ == "__main__":
    unittest.main()
