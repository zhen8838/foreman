import json
import runpy
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch


FOREMAN = Path(__file__).resolve().parents[1] / "bin" / "foreman"


class HcTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ns = runpy.run_path(str(FOREMAN))
        self.hc = self.ns["hc"]

    def _with_run(self, code: int, stdout: str = "", stderr: str = ""):
        seen = []

        def fake_run(argv, **_kwargs):
            seen.append(argv)
            return subprocess.CompletedProcess(argv, code, stdout, stderr)

        return seen, patch.dict(self.hc.__globals__, {"run": fake_run})

    def test_json_flag_follows_the_subcommand(self) -> None:
        seen, ctx = self._with_run(0, '{"address": "t7"}')
        with ctx:
            self.assertEqual(self.hc("run", "--bg", "--", "bash", "x"), {"address": "t7"})
        # after the subcommand, never at the end: there it would reach the program being run
        self.assertEqual(seen, [["hc", "run", "--json", "--bg", "--", "bash", "x"]])

    def test_error_carries_message_and_hint(self) -> None:
        err = json.dumps({"error": {"kind": "not_found", "message": "no terminal \"x\"",
                                    "hint": "see `hc ls --all`"}})
        _, ctx = self._with_run(3, stderr=err)
        with ctx, self.assertRaisesRegex(SystemExit, r'no terminal "x"\n.*hc ls --all'):
            self.hc("get", "--", "x")

    def test_unchecked_error_comes_back_with_its_exit_code(self) -> None:
        err = json.dumps({"error": {"kind": "blocked", "message": "blocked"}})
        _, ctx = self._with_run(9, stderr=err)
        with ctx:
            res = self.hc("send", "--", "x", "hi", check=False)
        self.assertEqual(res["exit"], 9)
        self.assertEqual(res["error"]["kind"], "blocked")

    def test_run_argv_detaches_and_labels(self) -> None:
        argv = self.ns["run_argv"]("x-impl", Path("/wt"),
                                   {"herdr.space": "sp1", "foreman.task": "x"},
                                   ["bash", "/s.sh", "/p.md"])
        self.assertEqual(argv, [
            "run", "--bg", "--no-parent", "--name", "x-impl", "--cwd", "/wt",
            "--label", "herdr.space=sp1", "--label", "foreman.task=x",
            "--", "bash", "/s.sh", "/p.md",
        ])


if __name__ == "__main__":
    unittest.main()
