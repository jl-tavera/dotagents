---
name: ripple
description: "Find what a change could break somewhere else, beyond the diff, and prove the one fact it's safe because of by running real code instead of writing it up. Use for \"ripple of X\", \"what could this break\", \"blast radius\", or a small diff you don't trust even after a PASS from /verify."
argument-hint: "[fixed point | file or symbol]"
---

*Adapted from [pstack](https://github.com/cursor/plugins/tree/main/pstack) (MIT).*

# Ripple

Find what a change breaks somewhere else, before it ships. `/verify` proves the change does what it promised on its own surface. Ripple is for the rest: the caller three hops away, the other language reading the same bytes, the teardown order.

Listing the callers is not the job. `grep` does that in a second. The job is the breakage grep won't show you.

## Don't trust your own writeup

A ripple writeup that sounds right is worthless. It reads as convincing whether or not it's true. So don't hand back the writeup. Find the one or two facts the whole thing depends on and prove them by running code.

### How sure are you

For each fact the change's safety depends on, get it as far down this list as is cheap, and say where it stopped.

1. You said so. Worthless on its own.
2. You pointed at the line. A real `file:line`, or the library's own source.
3. You showed the bad case can't happen. You walked the failure step by step and it doesn't reach.
4. You ran it. A script or test that calls the real code and fails loud if you're wrong.
5. You reproduced it in the running app.

Step 4 is usually one small script that imports the same library the app ships and calls the exact function you're worried about.

## Steps

1. **Read the change.** The diff since the fixed point (the argument, else `git merge-base HEAD origin/main`), the symbols it adds, changes and deletes, and what it now does differently, including the part the diff doesn't spell out. `git log -p` for the commits' reasoning; `gh pr view <n>` when there is a PR.
2. **Find the one fact it's safe because of.** Most changes that look risky are safe because of a single fact, like "this call only drops already-dead cache entries and does nothing else". Find that fact. If it holds, most risky cases are cleared at once. Spend your time here, not on a long list of maybes.
3. **Look where grep stops.** Read the source of the library you call, at its pinned version and with any local patch. Work out when things run: microtasks, unmount and teardown, effect order. Follow what a symbol search misses: the JSON an API returns, a DB column, a wire format, another language reading the same bytes, a feature flag, code three hops downstream.
4. **Be honest about each risk.** Give it a real chance of happening and a real cost if it does. Keep the risks you confirmed. List the ones you checked and cleared separately. Cite a real `file:line`; a search that finds nothing is still an answer; never make up a caller or an API.
5. **Prove the one fact.** Write a script or test that runs the real code, run it, and paste what happened.

For a wide change the one-fact framing stops working; `/review` is the better tool there.

## What to hand back

- **What it does.** What changed, including the part that isn't obvious.
- **The one fact it's safe because of.** State it, say which step of the ladder you got it to, and show the proof. If you couldn't prove it, write **unproven**.
- **Risks.** Each names how it breaks, the `file:line`, how likely and how bad, and how to check. Paste the proof for the ones that matter.
- **Cleared.** What you checked and why it's fine.
- **Before you merge.** The cheapest test or repro that catches the real bug, including the script you wrote.

Cite real code, and strip anything private before it goes anywhere public.
