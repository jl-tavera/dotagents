---
name: verify-skill
description: "Generate a project-local verify-<app> skill that drives the real app the way a user does — any language, framework or platform — with Launch, Doctor, Drive, Evidence and Cleanup sections and a feature map; or, when one exists, bring it back in line with the app. /verify follows it whenever it is present. Use for /verify-skill, \"make a verify skill for this repo\", \"audit the verify skill\", or when a project has no scripted way to prove UI, CLI or service behaviour."
disable-model-invocation: true
argument-hint: "[create | maintain]"
---

*Adapted from [pstack](https://github.com/cursor/plugins/tree/main/pstack) (MIT).*

# Verify skill

Every serious project needs a scripted way to drive the real app and prove behaviour: launch it, exercise a feature the way a user would, capture evidence. This skill writes that as a project-local skill, `.claude/skills/verify-<app>/`, tailored to the repo, and keeps it honest afterwards. The output is for the next agent, not for a human: it will be read cold, mid-task, by an agent that has never seen the app.

**Mode.** `create` when no `.claude/skills/verify-*/SKILL.md` exists in the project, `maintain` when one does; an explicit argument wins. Several candidates under maintain → ask which with AskUserQuestion.

## Create

### 1. Interview the repo, not the user

Answer these from the codebase and ask the user only what you cannot observe:

- **Surface:** what does a user actually touch? A web UI, a CLI or TUI, a desktop app, an API, a mobile app, a library? Pick the primary one and note the rest.
- **Run:** how does the app start locally? Prefer the repo's own documented dev command (package scripts, Makefile, README quickstart). Note ports, env vars, seed data, auth.
- **Drive:** how can an agent interact with it programmatically? Existing harnesses first — Playwright or Cypress specs, expect scripts, PTY helpers, curl-able endpoints, a debug port. Only then a generic recipe: `agent-browser` for web and Electron, a PTY or tmux session for CLI and TUI, plain HTTP for services.
- **Observe:** what evidence can be captured? Screenshots, ARIA snapshots, terminal transcripts, response bodies, logs, exit codes, DB state.
- **Isolate:** can two instances run side by side (ports, data dirs, profiles)? If not, say so in the generated skill: refusing to double-drive a shared instance beats corrupting the user's session.

If the checkout doesn't build or start as-is, fix that first, or report it precisely, before generating; a skill written against a broken base teaches wrong steps. When an irrelevant missing asset blocks startup (a static dir the API never serves, a sample config), the generated skill may create it, marked as verification scaffolding, and remove it in cleanup.

### 2. Generate the skill

Write `.claude/skills/verify-<app>/SKILL.md` with YAML frontmatter — `name: verify-<app>` and a `description` that names the app, the surface and when to reach for it; without frontmatter the skill never registers — and these sections, each grounded in what the interview found, no placeholders left:

- **Launch:** the exact command that starts the app for verification, and how to tell it's ready (a log line, a prompt). Launch reaches a usable state from an empty data dir, including migrations and seed data. Ready means usable, not just that a process answers: a database health check can pass while its init scripts are still running. Include teardown. For a short-lived CLI or TUI there is no server to keep alive: launch means build the binary (or install deps) once, then start each drive in its own isolated PTY or tmux session.
- **Doctor:** one read-only check that answers "is this instance worth driving?" — process up, right version or build, port owned by us, auth valid. An agent runs it first whenever anything looks off.
- **Drive:** the harness recipe with real selectors and commands from this repo, not examples. Prefer stable handles (ARIA labels, data attributes, prompt strings, route paths) over coordinates and tab order.
- **Evidence:** what to capture for a proof and where it goes. State the proof standards: exercise the real user path, not internal setters or test-only endpoints; capture the action and the resulting state, not just the final screen; verify side effects (files written, rows inserted, messages sent) alongside what's visible; mocks only where a production boundary already isolates the external system; a dry-run mode is verified by what it actually skips, not by its name.
- **Cleanup:** how to tear down instances the run created. Never kill by process name; kill what you started. Cleanup removes instances and scratch state, never the evidence: proof artifacts survive the teardown, in a location the skill names.
- **Helpers:** any script the skill ships is executable and its invocation is shown in the skill body. A helper the reader has to reverse-engineer is not a helper.

### 3. Seed the feature map

Create `.claude/skills/verify-<app>/features/README.md` plus one file per user-facing feature you can identify (the top 3–5 to start, from routes, commands, menus or docs). Follow the shape in [`references/feature-map-example/`](references/feature-map-example/): a README index, and one file per feature that answers, from the user's point of view, what the feature is, how to reach it, how to drive it with the harness, and what observable end state proves it works. The four H2s are `Sub-features`, `How to get to it (user POV)`, `Driving it with <harness>` and `Gotchas`. If the seed data lacks a precondition a journey needs, the journey reports a failure and the reason goes in that feature's `Gotchas`. Never weaken the journey to make it pass. The map is the repo's maintained verification source; a proof that drives one convenient entry point is incomplete when the map lists others.

### 4. Prove it before handing it over

Run its own instructions end to end once: launch, doctor, drive ONE mapped feature (one is enough; the map exists so later runs cover the rest), capture evidence, clean up. After cleanup, confirm the evidence still exists at the named location — a cleanup that eats the proof fails this step. Fix what fails, and run the generated cleanup after every failed iteration too, so broken attempts don't strand processes and ports. A generated skill that was never executed is a draft, not a deliverable. If you proved it in a stand-in for the real target (a container in place of a fresh VM, a local stack in place of a remote one), list every setup step the stand-in did that the target will not. Those stay unverified until a run on the real target covers them.

### 5. Hand off

The skill is project infrastructure: it lives in the project's `.claude/skills/` and is committed with it, so every person and agent drives the app the same way. Say what was generated, which feature the proof drove, and where the evidence is. `/verify` follows the skill from now on without being told. Point at `/verify-skill maintain` for keeping the map honest as the app changes; suggest a cadence only if asked.

## Maintain

A feature map rots the moment the app changes. The unit of rigour is the feature, not every sentence: cover every feature file from source and exercise every feature live.

**Outcome.** Exactly one, and say which:

- **clean** — every feature got source and live coverage; nothing worth shipping. No branch.
- **changed** — one branch of proven corrections. Then ask **"Ship it — run /ship"** (Recommended) / **"Not yet"** with AskUserQuestion; `/ship` starts only from that tap.
- **blocked** — coverage could not finish or a proven fix could not ship safely. Say exactly what blocked it.

**Edit scope.** Only the verify skill's own directory (its SKILL.md, `features/`, and any harness scripts it owns). Never product code: a behaviour the map describes that the app no longer does is either doc drift (fix the map) or a product regression (report it, don't paper over it in docs).

**Pass:**

1. **Locate.** The project-local skill whose body has Launch and Drive sections and a feature map.
2. **Index hygiene.** Read the feature map README and glob its sibling files. Fix missing, extra, duplicate or dead entries. Lightweight; no generated inventory.
3. **Source wave.** One `Explore` sub-agent per feature file, launched in parallel, briefed "do not edit files, do not drive the app". Each explains how the feature works from source, flags likely doc drift with citations, and returns one concise live-verification recipe. Return shape: feature summary / source entry points / likely drift or none / one recipe. Check `git status` afterwards.
4. **Reconcile.** Every feature file has a returned summary. Merge overlapping recipes into as few app states as practical. Spot-check cited drift; don't re-prove clean claims. Sweep recent churn for user-facing surfaces missing from the map — a concrete source path is required before calling one missing.
5. **Live pass.** Required even when source looks clean. You drive; follow the skill's own launch model (one long-lived instance driven serially for servers and UIs, a fresh isolated session per drive for short-lived CLIs). Exercise every feature at least once, holding three invariants whatever fails: (1) never drive an instance you haven't health-checked since it last did something surprising — doctor before the first drive, on each fresh session, and again after any failed drive; where doctor can't see the failure (a wedged UI on a healthy process), reset or relaunch rather than hope; (2) evidence captured so far survives every cleanup, checked at its named location, not assumed; (3) nothing a drive started outlives that drive's usefulness — failed-iteration residue is cleaned whether the session is stuck, exited or shared (for a shared instance, clean the residue, not the instance). A doctor failure caused by skill drift is drift: fix it under edit scope and retry once before calling the pass blocked. A feature that can't be reached is `verified-unreachable` only with the concrete prerequisite (auth, entitlement, OS, external state) and the route attempted; a map that omits that prerequisite has drift. Any harness fix gets re-driven live before it ships. Final teardown happens after the last drive, including those re-proofs; evidence stays.
6. **Triage.** Wrong or missing user-POV description → doc drift, fix it. Working behaviour the harness can't drive → harness gap, fix it (scripts executable, invocation in the skill body). App behaviour that's actually broken → product gap: report it to the user, keep it out of this branch.
7. **Ship or stop.** For changed: one branch, re-read every changed file first, then the tap question. For clean or blocked: no branch; report the outcome and the coverage honestly.

Keep concise run notes (features covered, unreachable prerequisites, confirmed drift, outcome) in the OS temp dir; don't commit them.
