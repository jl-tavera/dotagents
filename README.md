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

## Why this exists

These are my skills, built from a mix of [Matt Pocock's skills](https://github.com/mattpocock/skills) and Ponytail. The point is to control what context each agent gets, instead of dragging one long conversation from idea to merge:

- **One job per context window.** Planning (`grill` → `spec` → `issues`) stays in one window. Every ticket gets a fresh one (`/clear`, then `/build`). Anything that crosses a machine, harness or person goes through `/handoff`.
- **Handoffs are artifacts, not memory.** The spec and the tickets are GitHub issues. Terms go in `docs/glossary.md` and decisions in `docs/adr/`. The next agent reads those, not a transcript.
- **Sub-agents for scoped work.** `/review` runs three in parallel (standards, spec, lean) and reports them side by side, never merged into one verdict.
- **Best practice is built in, not remembered:** questions before code, vertical slices, TDD at the seams the ticket names, a three-axis review, layered commits that each pass the checks, rebase merges, and the simplest thing that works (`lazy`, always on).
- **You stay in the loop.** Every stop is a tappable question (Go? / Ship it? / Merge?), and hooks make sure the model can't skip one.

## How to use it

### The main flow: idea → ship

```mermaid
flowchart LR
    subgraph W1["Context window 1: planning"]
        G["/grill<br/>interview the idea"] --> S["/spec<br/>spec issue"]
        S --> I["/issues N<br/>one ticket per slice"]
    end
    I --> C(["/clear"])
    subgraph W2["Context window 2..n: one per ticket"]
        B["/build N"] --> P["trace + plan"]
        P --> Go{"Go?"}
        Go -- yes --> T["branch → /tdd<br/>red → green"]
        T --> K["checks"] --> R["/review<br/>standards · spec · lean"]
        R --> SI{"Ship it?"}
    end
    C --> B
    SI -- tap --> SH["/ship<br/>layered commits → PR"]
    SH --> M{"Merge?"}
    M -- tap --> D(["rebase-merged on main"])
    D -. next ticket .-> C
```

### What one ticket looks like

```mermaid
sequenceDiagram
    actor You
    participant Agent
    participant Hooks
    participant GitHub

    You->>Agent: /build 13
    Agent->>GitHub: read ticket 13
    Agent->>You: plan — Go?
    You->>Agent: tap Go
    Agent->>Agent: branch, /tdd red → green, checks
    Agent->>Hooks: git commit
    Hooks-->>Agent: allowed (not on main — no-commit-on-default.py)
    Agent->>Agent: /review (3 sub-agents)
    Agent->>You: Ship it?
    You->>Agent: tap Ship it
    Agent->>Hooks: start /ship
    Hooks-->>Agent: allowed (tap on record — tap-approval.py)
    Agent->>GitHub: push, open PR
    Agent->>You: Merge PR?
    You->>Agent: tap Merge
    Agent->>GitHub: gh pr merge --rebase --delete-branch
    Agent->>You: what's next (unblocked tickets, debts)
```

### Detours

```mermaid
flowchart TD
    Q["A question only running code can answer"] --> PR["/prototype<br/>throwaway branch"] --> BK["answer goes back into /grill"]
    BUG["Something's broken"] --> DG["/diagnose<br/>red-capable loop first"] --> A
    SP["A spare moment"] --> A["/arch<br/>≤5 deepening candidates"] --> GR["/grill on the one you pick"]
    X["New directory, harness or person"] --> H["/handoff"]
```

### At a phase boundary

The first one that fits wins:

1. **Continue**: the next phase needs this one word for word.
2. **`/clear`**: nothing here matters next.
3. **`/handoff`**: moving to a new directory, harness, or person.
4. **Sub-agent**: tightly scoped work that doesn't need steering.
5. **`/compact <what's next>`**: the default, and the last resort.

## Examples

**A new feature, end to end**

```
/grill I want users to export their data as CSV
   → questions in rounds; defaults listed under "Assumed"
/spec
   → issue #12: Problem · Solution · Slices · Seams under test · Not building
/issues 12
   → #13 export one table, #14 export all (blocked by #13), #15 download UI (blocked by #14)
/clear
/build 13
   → plan → Go? → feat/13-export-table → red → green → review → Ship it?
   → [tap] → PR #16 → Merge? → [tap] → merged; "#14 is unblocked"
/clear
/build 14
```

**A small fix that doesn't need a spec**

```
(ticket #20 already exists and is clear)
/build 20
```

**A bug**

```
/diagnose checkout total is off by one cent on some carts
   → builds a failing repro first, then theories, then the fix
/review main
/ship
```

**A design question that needs running code**

```
/grill should drafts autosave or save on blur?
   → "this needs a prototype"
/prototype
   → throwaway UI on prototype/autosave; you click through it
   → the answer goes back into the grill
```

**Keeping the codebase healthy**

```
/arch    → HTML report of up to 5 deepening candidates, then a grill on the one you pick
/audit   → ranked list of what to delete or replace with stdlib/native
/debt    → every `# lazy:` shortcut, its ceiling, and its upgrade trigger
```

**Reviewing work in progress or a branch**

```
/review main        → since main
/review HEAD~3      → the last three commits
```

**Handing off to another machine or harness**

```
/handoff continue slice #14 in Codex
   → a handoff doc in the OS temp dir; the new session starts from it
```

**Adjusting how lazy it is**

```
/lazy ultra   → push hard for less code
/lazy lite    → nudge only
/lazy off
```

## Reserved for you

`/spec`, `/issues`, `/build`, `/arch`, `/handoff`, `/debt`, `/audit` and `/guide` run only when you type them. `/ship` runs when you type it or tap **Ship it**. The model can't start them on its own (`tap-approval.py`), and can't read their `SKILL.md` to replay them by hand (`reserved-skills.py`). Commits and pushes on `main` are blocked (`no-commit-on-default.py`).

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
