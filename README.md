# dream

A Claude Code skill that keeps an agent's long-term memory honest. Run it once a day (by hand with `/dream`, or from a timer) and it:

1. reads a short digest of every Claude Code session since the last run,
2. checks each line of your injected memory file (`memory.md`) and Claude Code's auto-memory notes against that evidence,
3. fixes lines that drifted (passed deadlines, finished tasks, dead paths, relative dates like "next Friday" turned absolute), demotes long or historical lines to an append-only log,
4. promotes things you had to say twice into a feedback memory note,
5. flags what it could not settle as one-word questions for you.

Every edit names its evidence, and nothing is deleted: removed lines land verbatim in the log.

## Layout

```
skill/SKILL.md                    the skill (procedure and rules)
skill/scripts/transcript_digest.py  compact digest of recent session transcripts
skill/scripts/prune_memory.py     moves [RESOLVED]/[DONE] items and old session lines to the log
skill/scripts/dreamconf.py        reads .claude/dream.toml
config.example.toml
examples/dream-run, dream.service  headless runner + systemd unit
```

## Install

```bash
git clone https://github.com/ericxu1070/dream ~/Projects/dream
cd <your project>
ln -s ~/Projects/dream/skill .claude/skills/dream
cp ~/Projects/dream/config.example.toml .claude/dream.toml   # optional
```

The project needs a memory file with `## Things to revisit` and `## Recent sessions` sections, and a session log whose entries start `## [YYYY-MM-DD] <type> | <title>`, newest first. Scripts run from the project root and use only the Python 3.11+ standard library.

If you use several Claude Code accounts (`CLAUDE_CONFIG_DIR`), list every config dir under `profiles` so the digest sees all of their sessions.

## Tests

`python3 -m unittest discover tests` runs the pruner and the transcript digest on fixtures (resolved items and overflow move verbatim, a second prune is a no-op, tool results, subagent turns, and headless runs stay out of the digest).

## License

MIT
