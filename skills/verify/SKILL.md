---
name: verify
description: "Prove the change since a fixed point works on its real surface — run the command, drive the UI, call the endpoint, read the stored value back — capture the evidence, and return one verdict: PASS, FAIL or INCONCLUSIVE. Checks and reviews read the code; this runs it. Use when the user says \"verify this\", \"prove it works\", \"does it actually work\", \"show me evidence\", or asks to \"verify since X\"; /build runs it after the checks and before /review."
argument-hint: "[fixed point]"
---

*Adapted from [pstack](https://github.com/cursor/plugins/tree/main/pstack) (MIT).*

# Verify

"It compiles" is not evidence. Green tests are not evidence that the feature works either: they prove the cases someone thought to write. This skill runs the real artifact on the surface the change touches, captures what happened, and says so in one word. `/review` reads the diff; `/verify` runs it.

This skill proves. It does not fix. A FAIL goes back to whoever called it — `/build`, which fixes and reruns the checks, or the user.

## 1. Pin the change

The user's argument if given (a SHA, branch, tag, `HEAD~3`). Otherwise the merge-base with the default branch — `git merge-base HEAD origin/main` — and say so in one line; don't ask. `git diff <fixed-point>...HEAD --stat` and `git log <fixed-point>..HEAD --oneline` are the inventory of what has to be proven.

Find the ticket the way `/review` does: the number in the branch name `<type>/<issue>-<slug>` or in commit messages (`#123`, `Closes #45`) → `gh issue view <n>`. Its checkbox acceptance criteria are the list to prove: a criterion a user could check is a criterion you run. No ticket → the diff decides.

## 2. Pick the surface from the diff

Match the check to the change. Wrong surface is not a pass; neither is "couldn't run it".

| The diff touches | The check is |
|---|---|
| A CLI | Run the real command on a real input, the way a user would type it. |
| A UI | Walk the changed flow in the running app. If `.claude/skills/verify-*/SKILL.md` exists in the project, follow it: doctor, drive the mapped feature, evidence, cleanup. Otherwise launch the app the way the built-in `run` skill or the project's task runner does, and drive it with `agent-browser`. |
| An API or service | Send the real request; read the status and body, not the handler's unit test. |
| A parser, importer or migration | Replay a saved real input and compare the output with what the change promised. |
| Storage | Write through the user path, then read the value back through a second path (another query, the UI, the export). |
| A library | The smallest script that imports the built package and calls the changed function with a concrete input. |
| A perf claim | Run before and after, several times each; report median and range. A single run is a ballpark — say so. |

Several rows apply → several checks. Start with the one that reaches furthest into what the user touches.

## 3. Prove it, don't infer it

- **Exercise the real user path.** Not internal setters, not test-only endpoints, not a fixture that skips the part that changed.
- **Capture the action and the resulting state,** not only the final screen. A save status alone proves nothing; reopen the record.
- **Check side effects alongside what is visible:** the file written, the row inserted, the message sent.
- **Mocks only where a production boundary already isolates the external system.** Everything inside that boundary runs for real.
- **A dry-run mode is verified by what it actually skips** — files, network, git refs — not by its name. Some dry-runs still open a browser.
- **Check the real thing, not a proxy.** Process liveness directly, not through derived state; the actual value, not a cached or rendered copy; the diff, not the commit message.
- **When a check fails, suspect the observation method before the system.** Then suspect the system.
- **Script the check when you can.** A script a reviewer can rerun beats a one-time eyeball. Keep it with the evidence.
- **Never weaken a check to make it pass.** A precondition the environment lacks makes the check INCONCLUSIVE; it does not remove the assertion.

## 4. Evidence

Write it under `verify/<branch>/` in the OS temp dir (where `/handoff` writes too), and name the path in the verdict:

- CLI: the command, stdout, stderr, exit code.
- UI: a screenshot and an ARIA snapshot of the end state, with the app identity visible.
- HTTP: the request, the response status and body.
- Storage: the value as read back through the second path.
- A script: the script and its run.

Redact every secret first: write `<REDACTED>` in its place. Kill only what you started, never by process name. Cleanup removes instances and scratch state, never the evidence; confirm the evidence still exists after cleanup.

## 5. Verdict

The first line is one word:

- **PASS** — every surface the diff touches was exercised and behaved as promised, with evidence.
- **FAIL** — something the diff promised did not happen. Name the step, what was observed, and the evidence.
- **INCONCLUSIVE** — a check could not run. Say which, and why: credentials, a live service, no harness, no seed data. A confident report with no evidence is INCONCLUSIVE, not PASS.

Then a table — `surface | what ran | observed | evidence` — one row per check. Then `Not covered:` with the reason. Under 300 words.

Inside `/build … auto`, FAIL after a real fix attempt and INCONCLUSIVE both stop the ticket with `needs-human`; the verdict is the comment.

A small diff that still worries you after a PASS → `/ripple`. No scripted way to drive this app at all → `/verify-skill`.
