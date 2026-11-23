#!/usr/bin/env python3
"""Move resolved items and overflow session lines from memory.md into the session log."""
import argparse
import datetime
import os
import shutil
import sys
import tempfile
from pathlib import Path

import dreamconf

KEEP_SESSIONS = 10
MAX_LINES = 60
MAX_BYTES = 12000
SESSIONS = "## Recent sessions"
RESOLVED_PREFIXES = ("- [RESOLVED", "- [DONE")


def split_moves(lines):
    """Return (kept_lines, resolved, overflow) for memory.md split on newlines."""
    kept, resolved, overflow = [], [], []
    section = None
    sessions_seen = 0
    for line in lines:
        if line.startswith("## "):
            section = line.rstrip()
            sessions_seen = 0
        elif section == SESSIONS and line.startswith("- "):
            sessions_seen += 1
            if sessions_seen > KEEP_SESSIONS:
                overflow.append(line)
                continue
        elif section != SESSIONS and line.startswith(RESOLVED_PREFIXES):
            resolved.append(line)
            continue
        kept.append(line)
    return kept, resolved, overflow


def add_to_log(text, bullets, today):
    heading = f"## [{today}] prune | memory.md auto-prune"
    lines = text.split("\n")
    if heading in lines:
        i = lines.index(heading) + 1
        while i < len(lines) and not lines[i].startswith("## ["):
            i += 1
        while lines[i - 1] == "":
            i -= 1
        return "\n".join(lines[:i] + bullets + lines[i:])
    block = [heading, "", *bullets, ""]
    first = next((i for i, l in enumerate(lines) if l.startswith("## [")), None)
    if first is None:
        sep = "" if text.endswith("\n\n") or not text else ("\n" if text.endswith("\n") else "\n\n")
        return text + sep + "\n".join(block) + "\n"
    return "\n".join(lines[:first] + block + lines[first:])


def atomic_write(path, text):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        shutil.copymode(path, tmp)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def warn_if_large(name, text):
    n_lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    n_bytes = len(text.encode("utf-8"))
    if n_lines > MAX_LINES or n_bytes > MAX_BYTES:
        print(f"warning: {name} is {n_lines} lines, {n_bytes} bytes "
              f"(limit {MAX_LINES} lines, {MAX_BYTES} bytes)", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--memory", type=Path, default=dreamconf.load()["memory"])
    ap.add_argument("--log", type=Path, default=dreamconf.load()["log"])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    mem_text = a.memory.read_text(encoding="utf-8")
    kept, resolved, overflow = split_moves(mem_text.split("\n"))
    moved = resolved + overflow
    if not moved:
        print("nothing to prune")
        warn_if_large(a.memory.name, mem_text)
        return 0

    log_text = a.log.read_text(encoding="utf-8")
    present = set(log_text.split("\n"))
    fresh = []
    for line in moved:
        if line not in present:
            present.add(line)
            fresh.append(line)

    summary = f"moved {len(resolved)} resolved, {len(overflow)} session lines"
    new_mem = "\n".join(kept)
    if a.dry_run:
        print(f"dry run: {summary} ({len(fresh)} new to log)")
        for line in moved:
            print("   ", line[:100])
        return 0

    today = datetime.date.today().isoformat()
    if fresh:
        atomic_write(a.log, add_to_log(log_text, fresh, today))
    atomic_write(a.memory, new_mem)
    print(summary)
    if not a.dry_run:
        warn_if_large(a.memory.name, new_mem)
    return 0


if __name__ == "__main__":
    sys.exit(main())
