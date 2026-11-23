---
name: dream
description: Offline memory consolidation - check the injected memory file and the auto-memory notes against the session transcripts since the last run and the session log, correct what drifted, push detail down to the log, and keep the injected layer small. Use when the user says "dream", "consolidate memory", "clean up memory", or when started by a scheduled runner. Distinct from a note linter, which checks notes, not memory.
---

# Dream

Memory is layered. Each layer is smaller and more trusted than the one below it, and every session pays for the top two.

| Layer | Where | Loaded |
|---|---|---|
| Injected | the memory file (`memory` in `.claude/dream.toml`, default `memory.md`), and the auto-memory index `<profile>/projects/<project>/memory/MEMORY.md` | every session |
| Notes | the other files in that auto-memory folder | on recall |
| Log | the session log (`log`, default `logs/session-history.md`) | on demand |
| Transcripts | `<profile>/projects/<project>/*.jsonl` for every profile in `profiles` | via the digest script |

A wrong line in the injected layer is trusted by every later session. This run finds those lines and fixes them from evidence in the lower layers.

All paths are relative to the project root. When run headless, state assumptions and proceed; never ask. Paths in this file default to the values above; read `.claude/dream.toml` first if it exists.

## Write scope

Edit only the memory file, the session log, and files in the auto-memory folder. Everything else is read-only here, including `CLAUDE.md`, skills, and notes. A fix that belongs elsewhere becomes a flagged item (step 5).

## Steps

1. **Gather.** Read the memory file, the auto-memory `MEMORY.md` and each note it lists, and the log entries dated within the last 8 days. Find the newest `dream` entry among them: the window `N` is the days since that entry plus 1, or 8 when there is none. Run `python3 .claude/skills/dream/scripts/transcript_digest.py --days N` and read its output (a short window gives each session more room in the digest, so only the sessions since the last run are re-read). If `briefs` is set in the config, read the files matching that glob dated within the last N days: they are the only view of email and calendar this run gets, and they are evidence for step 2, not content to copy into memory.

2. **Correct.** For each line in the memory file and each auto-memory note, look for evidence from step 1 or from the project itself that it is now wrong:
   - A path, skill, script, or note it names no longer exists (check with `ls` or Glob).
   - A date or deadline it gives has passed.
   - A transcript, log entry, or brief shows the item was finished, dropped, or changed (a moved deadline, a reply that settles a "waiting on" item, a rejection).
   - Two lines contradict each other.
   - A session in the digest undid or re-corrected an edit an earlier dream run made. Leave the session's version in place and list the edit under `Reverted` in step 7.

   Fix the line in place when the evidence is direct. Prefix a settled revisit item with `[RESOLVED YYYY-MM-DD]` and leave it for the pruner. With no direct evidence, change nothing and flag it. Never invent a status.

3. **Demote.** A memory line over ~400 characters, one holding procedure or history rather than current state, or one restating state that its own artifact already shows (tracker counts, a note's contents, a file listing) moves to this run's log entry in full. Leave one line behind that states the current state and names the log entry.

4. **Promote.** Find what the user had to say twice: a correction repeated across sessions, a preference restated, an environment fact re-explained. Two sightings in the digest count, and so does one in the digest plus a `Seen once` line in an earlier dream entry from step 1. Write each as an auto-memory note (frontmatter and `MEMORY.md` pointer per the format of the existing notes), or update the note that already covers it. The note's `**Why:**` line names its evidence: the session dates and the user's words. Skip anything already in a `CLAUDE.md` and anything about one task only. Something seen once is not promoted: list it under `Seen once` in step 7 (what was said, session id, date) so a later run can match it. Most runs this step writes nothing.

5. **Flag.** Collect what you could not settle: a focus item with no activity in 30 days, a suspected stale decision, a fix that belongs in `CLAUDE.md` or a skill, or a chat answer worth keeping that no session filed as a note. Add each to the memory file's `## Things to revisit`, prefixed `DREAM <date>:` and phrased as a question the user can answer in a word. At most 3 `DREAM` items are open at once: leave the open ones in place with their original date, and add a new one only when there is room. A flag that does not fit goes in the log entry under `Flags held`.

6. **Prune.** Run `python3 .claude/skills/dream/scripts/prune_memory.py`. It moves `[RESOLVED]`/`[DONE]` items and session lines past 10 to the log and warns when the memory file is over 60 lines or 12000 bytes. On a warning, go back to step 3.

7. **Record.** Add one entry at the top of the session log, `## [YYYY-MM-DD] dream | memory consolidation`: each line corrected (old to new, with the evidence), each demoted line in full, each note promoted, each `Reverted` edit, each `Seen once` line, each flag. End it with `Tally: corrected N, demoted N, promoted N, reverted N, flagged N (window N days, N sessions)`, so the run's usefulness can be counted later with a grep. A run that changed nothing still writes the entry (the next run's window is measured from it), but only the `Seen once` lines and the tally. Add no `## Recent sessions` line unless something was corrected or flagged. When run headless and this run added new flags, `notify-send -a dream "Dream: N new items need you" "See Things to revisit"`; open flags from earlier runs do not notify again.

## Rules

- Move, never delete. Every removed line lands in the log entry verbatim.
- Evidence or no edit. Each correction in the log entry names its source (log entry date, session date, brief date, or the `ls` that failed).
- Follow the project's privacy rules in `CLAUDE.md`. The digest and the briefs may hold personal data; do not copy it into memory.
- Do not git-commit. Leave that to the user or their runner.
