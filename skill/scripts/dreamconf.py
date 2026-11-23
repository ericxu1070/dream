"""Load .claude/dream.toml from the project root (the current directory). Every key is optional."""
import re
import tomllib
from pathlib import Path

ROOT = Path.cwd()


def load():
    p = ROOT / ".claude" / "dream.toml"
    cfg = tomllib.loads(p.read_text()) if p.exists() else {}
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(ROOT))  # how Claude Code names a project's transcript dir
    return {
        "memory": ROOT / cfg.get("memory", "memory.md"),
        "log": ROOT / cfg.get("log", "logs/session-history.md"),
        "transcript_dirs": [Path(d).expanduser() / "projects" / slug
                            for d in cfg.get("profiles", ["~/.claude"])],
    }
