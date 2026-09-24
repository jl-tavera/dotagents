---
name: build
description: "Build one ticket: read it, trace the code, plan it and ask to go, branch, TDD at the ticket's seams, run the checks, review, then ask to ship."
disable-model-invocation: true
argument-hint: "[ticket #]"
---

# Build

Build the ticket the user names. One ticket per context window.

**Every stop is a tappable question.** Whenever you need the user — the go-ahead, a decision, shipping — ask with the AskUserQuestion tool, never with a question written in the reply: a pending question notifies them in the Remote Control app, a reply that just ends does not. Say what the choice is for before asking it, recommended option first. Answering a question never changes the permission mode. Plan here, in the reply, never with EnterPlanMode/ExitPlanMode: approving a plan from the phone can't return the session to auto.

1. **Read the ticket and its parent.** `gh issue view <n> --comments`, then the `Part of #<spec>` issue. The ticket's **Seams under test** and **Not in this ticket** are binding.
2. **Understand before you climb.** Trace every file the change touches and the actual flow end to end. Only then pick the ladder rung. The smallest change in the wrong place is a second bug. Read-only until step 3 is answered: no branch, no edits.
3. **Plan, then ask to go.** Write the plan in the reply — what gets built and where, the seams, what's assumed. Then ask **"Go"** (Recommended) / **"Change the plan"**. A decision that changes the build rides in the same AskUserQuestion call, not a later one. Nothing is touched before "Go"; "Change the plan" means revise and ask again.
4. **Branch.** `git switch -c <type>/<issue>-<slug>` (so `feat/35-mirror-and-add`). Never work on `main` — a hook blocks commits there. Cut it now, after the reading, so it is named with the ticket in mind.
5. **`/tdd` at the ticket's seams.** Call the Skill tool with `tdd`. Red → green, one slice at a time. Don't re-ask which seams.
6. **Checks.** Run the checks for the areas touched — the list is in `CLAUDE.md § Agent skills`. Single test files as you go; the area's full suite once at the end.
7. **`/review`.** Call the Skill tool with `review`. Fix what's real; note what you decided against and why.
8. **Ask to ship.** Say what was built and what was left, then ask **"Ship it — run /ship"** (Recommended) / **"Not yet"**. On "Ship it", call the Skill tool with `ship`. That tap is the only way in — `tap-approval.py` refuses the call without it — so never invoke `ship` on your own.

Output per the ladder: the code, then at most three lines — `skipped: X, add when Y`.
