# dotagents

My agent setup — skills, hooks and rules — kept in one repo and linked into every harness I use. Project-agnostic: nothing here assumes a particular codebase.

```
python install.py
```

Safe to re-run. It links, never copies, so editing a file here changes it everywhere at once:

| Path | Harness |
|---|---|
| `~/.claude/skills/<name>` → `skills/<name>` | Claude Code |
| `~/.agents/skills/<name>` → `skills/<name>` | Codex and other [Agent Skills](https://agentskills.io) harnesses |
| `~/.claude/hooks` → `hooks/`, wiring from `harness/claude/hooks.json` merged into `~/.claude/settings.json` (backed up first) | Claude Code |
| `~/.claude/CLAUDE.md` (`@`-imports `AGENTS.md`), `~/.codex/AGENTS.md` → `AGENTS.md` | Claude Code, Codex |

Anything already at one of those paths that isn't a link here is left alone and reported. On Windows, directory links are junctions (no admin); the one file link needs Developer Mode.

## Layout

- `AGENTS.md` — rules every harness should follow.
- `skills/` — one folder per skill, `SKILL.md` in the open Agent Skills format.
- `hooks/` — Python hooks, JSON on stdin, exit code out. Each looks for skills in the project's `.claude/` first, then `~/.claude/`. Test: `python hooks/test_tap_approval.py`.
- `harness/<name>/` — the wiring one harness needs. Adding a harness = a folder here and a few lines in `install.py`.

## Skills

The idea → ship chain: `grill` → `spec` → `issues` → `build` (`tdd`, `review`) → `ship`. `guide` maps it on one screen.

- `arch` — find deepening opportunities, report the top candidates, grill the one you pick
- `audit` — whole-repo hunt for over-engineering, ranked
- `build` — build one ticket: trace, plan, branch, TDD, check, review, then offer to ship
- `debt` — harvest `lazy:` shortcut comments into one ledger
- `deep-modules` — shared vocabulary for designing deep modules
- `diagnose` — loop for hard bugs and performance regressions
- `domain` — the project glossary (`docs/glossary.md`) and ADRs (`docs/adr/`)
- `grill` — interview until the build-changing questions are settled
- `guide` — which skill fits, in what order
- `handoff` — compact a conversation into a handoff doc
- `issues` — split a spec into vertical-slice GitHub issues with dependency links
- `lazy` — the simplest solution that works; always on via the SessionStart hook
- `prototype` — throwaway prototype to answer a design question
- `review` — review since a fixed point: standards, spec, lean
- `ship` — layered commits → PR → merge; starts only on the user's say-so (`tap-approval.py`)
- `spec` — turn the conversation into a spec issue
- `tdd` — red → green at the ticket's seams
- `tickets` — impact analysis and dev-ready tickets in ClickUp

## Hooks

- `lazy-activate.py` — injects the `lazy` ruleset into every session and sub-agent; intensity from `.claude/lazy-mode`.
- `no-commit-on-default.py` — refuses `git commit`/`git push` on the default branch.
- `reserved-skills.py` — refuses to open the instructions of a user-only skill.
- `tap-approval.py` — lets a user's tap on a question start an `approval: tap` skill, and nothing else.

## Not here

Third-party skills, installed on their own: [agent-browser](https://github.com/vercel-labs/agent-browser), [Context7](https://github.com/upstash/context7).
