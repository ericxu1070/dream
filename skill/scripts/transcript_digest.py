#!/usr/bin/env python3
"""Print a compact digest of recent Claude Code sessions: human messages and each turn's final reply."""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import dreamconf

HUMAN_MAX = 600
REPLY_MAX = 400
HEADLESS = ("/daily-brief", "/dream")
NOT_HUMAN_PREFIXES = (
    "<local-command-", "<task-notification", "<bash-", "<system-reminder",
    "Another Claude session sent a message", "[Request interrupted",
)
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
COMMAND = re.compile(r"<command-name>(/[^<]+)</command-name>(?:.*?<command-args>(.*?)</command-args>)?", re.S)


def clip(s, n):
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 3] + "..."


def human_text(content):
    """Return what the human typed in a user record, or None if it is not a human message."""
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        content = "\n".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    if not isinstance(content, str):
        return None
    content = REMINDER.sub("", content).strip()
    m = COMMAND.search(content)
    if m:
        return (m.group(1) + " " + (m.group(2) or "")).strip()
    if not content or content.startswith(NOT_HUMAN_PREFIXES):
        return None
    return content


def assistant_text(content):
    if not isinstance(content, list):
        return ""
    parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
    return REMINDER.sub("", "\n".join(parts)).strip()


def parse_session(path):
    """Return (first_timestamp, [(role, text)]) streaming the file; role is 'H' or 'A'."""
    first_ts = None
    entries = []
    pending = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if not isinstance(r, dict) or r.get("isSidechain") or r.get("isMeta"):
                continue
            kind = r.get("type")
            if kind not in ("user", "assistant"):
                continue
            msg = r.get("message")
            if not isinstance(msg, dict):
                continue
            if first_ts is None:
                first_ts = r.get("timestamp")
            if kind == "user":
                text = human_text(msg.get("content"))
                if text is None:
                    continue
                if pending:
                    entries.append(("A", pending))
                    pending = None
                entries.append(("H", text))
            else:
                text = assistant_text(msg.get("content"))
                if text:
                    pending = text
    if pending:
        entries.append(("A", pending))
    return first_ts, entries


def render(sid, ts, entries, budget):
    """Render one session within budget chars; return (text, truncated)."""
    head = f"## session {sid} {ts or '?'}"
    lines = [("H: " + clip(t, HUMAN_MAX)) if r == "H" else ("A: " + clip(t, REPLY_MAX))
             for r, t in entries]
    room = budget - len(head) - 1
    if sum(len(l) + 1 for l in lines) <= room:
        return "\n".join([head, *lines]), False
    # Decisions land at the end of a session, so the tail gets two thirds of the budget.
    room -= 40
    first, used = [], 0
    for l in lines:
        if used + len(l) + 1 > room // 3:
            break
        first.append(l)
        used += len(l) + 1
    last, used = [], 0
    for l in reversed(lines[len(first):]):
        if used + len(l) + 1 > room - room // 3:
            break
        last.append(l)
        used += len(l) + 1
    omitted = len(lines) - len(first) - len(last)
    return "\n".join([head, *first, f"[{omitted} messages omitted]", *reversed(last)]), True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=float, default=7)
    ap.add_argument("--project-dir", type=Path, action="append",
                    help="repeatable; default: this project's transcript dir in every profile in .claude/dream.toml")
    ap.add_argument("--max-chars", type=int, default=150000)
    a = ap.parse_args()

    cutoff = time.time() - a.days * 86400
    dirs = a.project_dir or dreamconf.load()["transcript_dirs"]
    files = [p for d in dirs if d.is_dir() for p in d.glob("*.jsonl") if p.stat().st_mtime >= cutoff]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    sessions = []
    for p in files:
        ts, entries = parse_session(p)
        first = next((t for r, t in entries if r == "H"), None)
        if first is None or first.startswith(HEADLESS):
            continue
        sessions.append((p.stem, ts, entries))

    footer_room = 120
    remaining = a.max_chars - footer_room
    blocks, truncated = [], 0
    for i, (sid, ts, entries) in enumerate(sessions):
        budget = remaining // (len(sessions) - i)
        text, cut = render(sid, ts, entries, budget)
        blocks.append(text)
        remaining -= len(text) + 2
        truncated += cut
    print("\n\n".join(blocks))
    print(f"\n[{len(sessions)} sessions included, {truncated} truncated]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
