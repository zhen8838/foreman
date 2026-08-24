import json
import runpy
import tempfile
import unittest
from pathlib import Path

FOREMAN = Path(__file__).resolve().parents[1] / "bin" / "foreman"


class PreDoneHookTest(unittest.TestCase):
    def setUp(self) -> None:
        self.namespace = runpy.run_path(str(FOREMAN))
        self.run_hook = self.namespace["run_pre_done_hook"]
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.worktree = self.root / "worktree"
        self.worktree.mkdir()
        self.output = self.root / "hook.json"
        self.hook = self.root / "pre-done.sh"
        self.job = {
            "task": "example",
            "path": str(self.worktree),
            "main": str(self.root),
            "branch": "feat/example",
            "mode": "solo",
            "brief": "do it",
            "plan": "",
            "agents": {"solo": {"pane": "w1:p1", "kind": "pi"}},
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_passes_finish_context_to_hook(self) -> None:
        self.hook.write_text(
            "#!/usr/bin/env bash\n"
            "python3 - <<'PY'\n"
            "import json, os\n"
            f"with open({str(self.output)!r}, 'w') as stream:\n"
            "    json.dump({\n"
            "        'task': os.environ['FOREMAN_TASK'],\n"
            "        'remove': os.environ['FOREMAN_REMOVE_WORKTREE'],\n"
            "        'agents': json.loads(os.environ['FOREMAN_AGENTS_JSON']),\n"
            "        'cwd': os.getcwd(),\n"
            "    }, stream)\n"
            "PY\n",
            encoding="utf-8",
        )
        self.hook.chmod(0o755)

        self.run_hook({"hooks": {"pre_done": str(self.hook)}}, self.job, True)

        result = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(result["task"], "example")
        self.assertEqual(result["remove"], "1")
        self.assertEqual(result["agents"], self.job["agents"])
        self.assertEqual(result["cwd"], str(self.worktree))

    def test_failure_stops_teardown(self) -> None:
        self.hook.write_text("#!/usr/bin/env bash\nexit 7\n", encoding="utf-8")
        self.hook.chmod(0o755)

        with self.assertRaisesRegex(SystemExit, "pane, worktree and ledger were kept"):
            self.run_hook({"hooks": {"pre_done": str(self.hook)}}, self.job, False)


if __name__ == "__main__":
    unittest.main()
