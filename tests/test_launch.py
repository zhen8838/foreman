import json
import runpy
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


FOREMAN = Path(__file__).resolve().parents[1] / "bin" / "foreman"

# Stands in for the agent: records what it was started with, then exits.
FAKE_AGENT = """\
import json, os, sys
with open(os.environ["PROBE_OUT"], "w") as fh:
    json.dump({"argv": sys.argv[1:], "cwd": os.getcwd(),
               "task": os.environ.get("FOREMAN_TASK"),
               "from_hook": os.environ.get("FROM_HOOK")}, fh)
"""


class LaunchScriptTest(unittest.TestCase):
    """Runs the generated script under a real bash: the hook really is sourced."""

    def setUp(self) -> None:
        self.ns = runpy.run_path(str(FOREMAN))
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "agent.py").write_text(FAKE_AGENT)
        self.out = self.root / "out.json"
        self.prompt = self.root / "prompt.md"
        self.prompt.write_text("You are x-impl.\nSecond line.\n")
        self.args_file = self.root / "args.json"
        self.elsewhere = self.root / "elsewhere"
        self.elsewhere.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _run(self, hook_body: str | None) -> subprocess.CompletedProcess:
        hook = None
        if hook_body is not None:
            hook = self.root / "hook.sh"
            hook.write_text(hook_body)
        script = self.root / "launch.sh"
        script.write_text(self.ns["launch_script"](
            [sys.executable, str(self.root / "agent.py"), "--model", "m"],
            {"FOREMAN_TASK": "x", "PROBE_OUT": str(self.out)}, hook, self.args_file))
        return subprocess.run(["bash", str(script), str(self.prompt)], cwd=self.root,
                              text=True, capture_output=True)

    def test_hook_exports_cd_and_arguments_reach_the_agent(self) -> None:
        proc = self._run(
            "export FROM_HOOK=\"yes $#\"\n"
            f"cd {self.elsewhere}\n"
            "printf '%s' '[\"--ssh\", \"round:/w s\"]' > \"$FOREMAN_AGENT_ARGS_FILE\"\n")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        got = json.loads(self.out.read_text())
        self.assertEqual(got["argv"], ["--model", "m", "--ssh", "round:/w s",
                                       "You are x-impl.\nSecond line."])
        self.assertEqual(got["cwd"], str(self.elsewhere))
        self.assertEqual(got["task"], "x")
        self.assertEqual(got["from_hook"], "yes 0")  # no arguments leak into the hook
        self.assertFalse(self.args_file.exists())

    def test_without_hook_the_prompt_is_the_last_argument(self) -> None:
        proc = self._run(None)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(self.out.read_text())["argv"],
                         ["--model", "m", "You are x-impl.\nSecond line."])

    def test_hook_failure_ends_the_script_with_its_code(self) -> None:
        proc = self._run("echo 'wheel build failed' >&2\nreturn 4\n")
        self.assertEqual(proc.returncode, 4)
        self.assertIn("wheel build failed", proc.stderr)
        self.assertIn("source_env hook.sh failed (exit 4)", proc.stderr)
        self.assertFalse(self.out.exists())

    def test_malformed_arguments_are_refused(self) -> None:
        proc = self._run("echo '{\"ssh\": 1}' > \"$FOREMAN_AGENT_ARGS_FILE\"\n")
        self.assertEqual(proc.returncode, 98)
        self.assertIn("JSON array of strings", proc.stderr)
        self.assertFalse(self.out.exists())


class WaitReadyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.wait_ready = runpy.run_path(str(FOREMAN))["wait_ready"]
        self.calls = []

    def _run(self, gets: list[dict], screen: str = "", timeout: float = 100):
        replies = iter(gets)
        clock = iter(range(0, 1000))

        def fake_hc(cmd, *args, check=True):
            self.calls.append((cmd, *args))
            if cmd == "get":
                return next(replies)
            if cmd == "read":
                return {"text": screen}
            return {}

        fake_time = types.SimpleNamespace(sleep=lambda _s: None,
                                          monotonic=lambda: next(clock))
        table = {"trust_prompt": ["Yes, I trust this folder"], "trust_keys": ["down", "enter"]}
        with patch.dict(self.wait_ready.__globals__, {"hc": fake_hc, "time": fake_time}):
            self.wait_ready("t7", "x-impl", table, timeout)

    def test_first_status_report_means_ready(self) -> None:
        self._run([{"state": "live", "reported": False},
                   {"state": "live", "reported": True}])
        self.assertNotIn("keys", [c[0] for c in self.calls])

    def test_trust_dialog_is_answered_once(self) -> None:
        self._run([{"state": "live", "reported": False},
                   {"state": "live", "reported": False},
                   {"state": "live", "reported": True}],
                  screen="❯ No, exit\n  Yes, I trust this folder")
        keys = [c for c in self.calls if c[0] == "keys"]
        self.assertEqual(keys, [("keys", "--", "t7", "down", "enter")])

    def test_exit_before_reporting_shows_output_and_removes_it(self) -> None:
        with self.assertRaisesRegex(SystemExit, r"(?s)exited 4 .*Last output:\nboom"):
            self._run([{"state": "finished", "exit_code": 4}], screen="boom")
        self.assertIn(("rm", "--", "t7"), self.calls)

    def test_timeout_leaves_it_running_and_says_where_to_look(self) -> None:
        with self.assertRaisesRegex(SystemExit, "(?s)did not report in .*hc attach x-impl"):
            self._run([{"state": "live", "reported": False}] * 10, timeout=3)
        self.assertNotIn("rm", [c[0] for c in self.calls])
        self.assertNotIn("kill", [c[0] for c in self.calls])


class LaunchAgentTest(unittest.TestCase):
    SETTINGS = {"kinds": {"claude": {"command": ["claude"], "args": ["--x"],
                                     "effort_flag": ["--effort", "{effort}"]}}}

    def _launch(self, jobs: Path, job: dict, info: dict):
        ns = runpy.run_path(str(FOREMAN))
        launch_agent = ns["launch_agent"]
        calls, waits = [], []

        def fake_hc(*args, check=True):
            calls.append(args)
            return {"address": "t1b"}

        with patch.dict(launch_agent.__globals__, {
            "hc": fake_hc, "JOBS": jobs,
            "wait_ready": lambda *a: waits.append(a),
        }):
            addr = launch_agent("review", info, job=job, settings=self.SETTINGS, project={},
                                prompt="hello", prompt_name="prompt", plan=ns["Plan"](False))
        return addr, calls, waits

    @staticmethod
    def _job(**extra) -> dict:
        return {"task": "x", "path": "/wt", "main": "/main", "branch": "x", "mode": "pair",
                "space": "sp1", "brief": "", "plan": "", **extra}

    def test_terminal_is_detached_labelled_and_runs_the_script(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            jobs = Path(tmp) / "jobs"
            info = {"handle": "x-rev", "kind": "claude", "effort": "high"}
            # the job's one tab: impl and review split it
            addr, calls, waits = self._launch(jobs, self._job(tab="tb1"), info)

            self.assertEqual(addr, "t1b")
            script, prompt = jobs / "x" / "review.launch.sh", jobs / "x" / "review.prompt.md"
            self.assertEqual(calls, [(
                "run", "--bg", "--no-parent", "--name", "x-rev", "--cwd", "/wt",
                "--label", "herdr.space=sp1", "--label", "herdr.tab=tb1",
                "--label", "foreman.task=x", "--label", "foreman.role=review",
                "--", "bash", str(script), str(prompt),
            )])
            self.assertEqual(prompt.read_text(), "hello\n")
            self.assertIn("exec claude --x --effort high", script.read_text())
            self.assertIn("export FOREMAN_ROLE=review", script.read_text())
            self.assertEqual(waits[0][:2], ("t1b", "x-rev"))

    def test_ledger_with_a_tab_per_role_keeps_its_tabs(self) -> None:
        # written before a pair shared its tab; a restart must go back where the role was
        with tempfile.TemporaryDirectory() as tmp:
            info = {"handle": "x-rev", "tab": "tb2", "kind": "claude"}
            _, calls, _ = self._launch(Path(tmp) / "jobs", self._job(), info)
        self.assertIn("herdr.tab=tb2", calls[0])


if __name__ == "__main__":
    unittest.main()
