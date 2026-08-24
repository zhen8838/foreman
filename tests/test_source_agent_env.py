import json
import os
import re
import runpy
import shlex
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


FOREMAN = Path(__file__).resolve().parents[1] / "bin" / "foreman"


class SourceAgentEnvTest(unittest.TestCase):
    def setUp(self) -> None:
        self.namespace = runpy.run_path(str(FOREMAN))
        self.source_agent_env = self.namespace["source_agent_env"]
        self.plan = self.namespace["Plan"](False)
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.hook = self.root / "hook.sh"
        self.hook.write_text("return 0\n")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    @staticmethod
    def _args_file(command: str) -> Path:
        value = re.search(r"export FOREMAN_AGENT_ARGS_FILE=([^;]+)", command)
        assert value
        return Path(shlex.split(value.group(1))[0])

    def test_hook_can_return_runtime_agent_arguments(self) -> None:
        marker = f"__FOREMAN_ENV_{os.getpid()}_123__"

        def fake_herdr(*args):
            if args[:3] == ("pane", "run", "w1:p1"):
                self._args_file(args[3]).write_text(json.dumps(["--ssh", "round:/workspace/round"]))
            return {}

        def fake_run(args, **_kwargs):
            output = f"{marker} OK 0\n" if args[1:3] == ["pane", "read"] else ""
            return subprocess.CompletedProcess(args, 0, output, "")

        globals_patch = {
            "JOBS": self.root / "jobs",
            "herdr": fake_herdr,
            "run": fake_run,
            "time": types.SimpleNamespace(time_ns=lambda: 123),
        }
        with patch.dict(self.source_agent_env.__globals__, globals_patch):
            result = self.source_agent_env(
                {"hooks": {"source_env": str(self.hook)}}, "w1:p1", {}, self.plan
            )

        self.assertEqual(result, ["--ssh", "round:/workspace/round"])
        self.assertEqual(list((self.root / "jobs").iterdir()), [])

    def test_hook_failure_reports_pane_output_without_waiting_for_timeout(self) -> None:
        marker = f"__FOREMAN_ENV_{os.getpid()}_123__"

        def fake_run(args, **_kwargs):
            output = (
                "tileops setup-worktree: [TileFoundry wheel] failed (exit 2)\n"
                f"{marker} FAIL 2\n"
                if args[1:3] == ["pane", "read"]
                else ""
            )
            return subprocess.CompletedProcess(args, 0, output, "")

        globals_patch = {
            "JOBS": self.root / "jobs",
            "herdr": lambda *_args: {},
            "run": fake_run,
            "time": types.SimpleNamespace(time_ns=lambda: 123),
        }
        with patch.dict(self.source_agent_env.__globals__, globals_patch):
            with self.assertRaisesRegex(SystemExit, r"TileFoundry wheel.*failed"):
                self.source_agent_env(
                    {"hooks": {"source_env": str(self.hook)}}, "w1:p1", {}, self.plan
                )

    def test_hook_status_uses_wait_match_when_snapshot_lags(self) -> None:
        marker = f"__FOREMAN_ENV_{os.getpid()}_123__"

        def fake_run(args, **_kwargs):
            output = ""
            if args[1:3] == ["pane", "wait-output"]:
                output = json.dumps({"result": {"matched_line": f"{marker} OK 0"}})
            return subprocess.CompletedProcess(args, 0, output, "")

        globals_patch = {
            "JOBS": self.root / "jobs",
            "herdr": lambda *_args: {},
            "run": fake_run,
            "time": types.SimpleNamespace(time_ns=lambda: 123),
        }
        with patch.dict(self.source_agent_env.__globals__, globals_patch):
            result = self.source_agent_env(
                {"hooks": {"source_env": str(self.hook)}}, "w1:p1", {}, self.plan
            )

        self.assertEqual(result, [])

    def test_runtime_arguments_follow_configured_agent_arguments(self) -> None:
        start_agent = self.namespace["start_agent"]
        calls = []

        def fake_herdr(*args):
            calls.append(args)
            return {}

        def fake_run(args, **_kwargs):
            return subprocess.CompletedProcess(args, 1, "", "")

        settings = {
            "kinds": {
                "pi": {
                    "args": [],
                    "model_flag": ["--model", "{model}"],
                    "effort_flag": ["--thinking", "{effort}"],
                }
            }
        }
        spec = {"kind": "pi", "model": "openai-codex/gpt", "effort": "high"}
        with patch.dict(start_agent.__globals__, {"herdr": fake_herdr, "run": fake_run}):
            start_agent(
                "round", "w1:p1", spec, settings, self.plan,
                ["-e", "/pi/ssh.ts", "--ssh", "round:/workspace/round"],
            )

        self.assertEqual(calls, [(
            "agent", "start", "round", "--kind", "pi", "--pane", "w1:p1",
            "--timeout", "60000", "--", "--model", "openai-codex/gpt",
            "--thinking", "high", "-e", "/pi/ssh.ts", "--ssh",
            "round:/workspace/round",
        )])


if __name__ == "__main__":
    unittest.main()
