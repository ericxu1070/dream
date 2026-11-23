"""Fixture tests for the dream scripts. Run: python3 -m unittest discover tests"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "skill" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import prune_memory  # noqa: E402
import transcript_digest  # noqa: E402


def run(script, *args, cwd):
    r = subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise AssertionError(r.stderr)
    return r.stdout


class PruneTest(unittest.TestCase):
    MEMORY = "\n".join([
        "# Memory", "", "## Things to revisit",
        "- [RESOLVED 2026-11-20] reply to the reader", "- still open: pick a thesis topic", "",
        "## Recent sessions", *[f"- session {i}" for i in range(1, 13)], "",
    ])

    def test_split_moves_resolved_items_and_sessions_past_ten(self):
        kept, resolved, overflow = prune_memory.split_moves(self.MEMORY.split("\n"))
        self.assertEqual(resolved, ["- [RESOLVED 2026-11-20] reply to the reader"])
        self.assertEqual(overflow, ["- session 11", "- session 12"])
        self.assertIn("- still open: pick a thesis topic", kept)

    def test_end_to_end_moves_lines_verbatim_and_never_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            mem, log = Path(d, "memory.md"), Path(d, "log.md")
            mem.write_text(self.MEMORY)
            log.write_text("# Log\n\n## [2026-11-01] build | older entry\n\nbody\n")
            run("prune_memory.py", "--memory", str(mem), "--log", str(log), cwd=d)
            run("prune_memory.py", "--memory", str(mem), "--log", str(log), cwd=d)  # second run is a no-op
            text = log.read_text()
            self.assertEqual(text.count("- session 12"), 1)
            self.assertLess(text.index("prune | memory.md auto-prune"), text.index("older entry"))  # newest first
            self.assertNotIn("RESOLVED", mem.read_text())


class DigestTest(unittest.TestCase):
    def write_session(self, d, name, records):
        Path(d, name).write_text("\n".join(json.dumps(r) for r in records) + "\n")

    def user(self, content, **kw):
        return {"type": "user", "timestamp": "2026-11-22T10:00:00Z", "message": {"content": content}, **kw}

    def asst(self, text):
        return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}

    def test_digest_keeps_human_turns_and_final_replies_only(self):
        with tempfile.TemporaryDirectory() as d:
            self.write_session(d, "a.jsonl", [
                self.user("<system-reminder>noise</system-reminder>please fix the tracker"),
                self.asst("working on it"),
                self.user([{"type": "tool_result", "content": "tool output"}]),
                self.asst("Fixed the tracker."),
                self.user("side question", isSidechain=True),
            ])
            self.write_session(d, "b.jsonl", [self.user("<command-name>/dream</command-name>"), self.asst("dreamt")])
            out = run("transcript_digest.py", "--project-dir", d, "--days", "1", cwd=d)
            self.assertIn("H: please fix the tracker", out)
            self.assertIn("A: Fixed the tracker.", out)
            self.assertNotIn("working on it", out)      # only each turn's final reply
            self.assertNotIn("tool output", out)
            self.assertNotIn("side question", out)
            self.assertNotIn("dreamt", out)             # headless runs are skipped
            self.assertIn("[1 sessions included", out)

    def test_render_truncates_the_middle_and_keeps_the_end(self):
        entries = [("H", f"message {i} " + "x" * 200) for i in range(50)]
        text, cut = transcript_digest.render("s", "t", entries, 3000)
        self.assertTrue(cut)
        self.assertIn("messages omitted", text)
        self.assertIn("message 49", text)
        self.assertLessEqual(len(text), 3000)


class ConfTest(unittest.TestCase):
    def test_profiles_map_to_claude_transcript_dirs(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, ".claude").mkdir()
            Path(d, ".claude", "dream.toml").write_text('profiles = ["~/.claude", "/x/.claudep"]\n')
            out = subprocess.run([sys.executable, "-c", "import dreamconf; print(dreamconf.load()['transcript_dirs'])"],
                                 cwd=d, env={"PYTHONPATH": str(SCRIPTS)}, capture_output=True, text=True).stdout
            slug = "".join(c if c.isalnum() else "-" for c in str(Path(d).resolve()))
            self.assertIn(f"/x/.claudep/projects/{slug}", out)


if __name__ == "__main__":
    unittest.main()
