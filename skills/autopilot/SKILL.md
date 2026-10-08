---
name: autopilot
description: "Build, ship and merge a queue of tickets unattended: one fresh headless /build <n> auto session per ticket, in dependency order, stopping at the first ticket that needs a human. This chat is the control room."
disable-model-invocation: true
argument-hint: "[51-55 | 51 53 54 | empty = every ready-for-agent ticket] [--max N]"
---

# Autopilot

Start the queue and report on it. You don't build anything here: every ticket runs in its own fresh `claude -p "/build <n> auto"` session, started by the script next to this file.

1. **Start it in the background**, from the project root, with the user's arguments as given:
   `python ~/.claude/skills/autopilot/autopilot.py $ARGUMENTS` with `run_in_background: true`. Then watch its output with Monitor so each line reaches the chat as it's printed.
2. **Relay milestones** as they come: one short line each (`#51 merged ✓`, `#52 started: <title>`). Don't add commentary to routine lines.
3. **On a `STOPPED` line**, read the ticket (`gh issue view <n> --comments`) and say in two or three lines what it needs from the user and how to resume: answer or fix on the ticket, remove the `needs-human` label, run `/autopilot` again.
4. **While it runs**, the user may ask:
   - "how's it going?": summarise the output so far.
   - "stop after this one": create the STOP file whose path the script printed. The current ticket finishes and the run stops before the next one.
   - "stop now": stop the background task. Its branch stays where it was, so say which ticket was mid-flight.
   - the details of a ticket: point to `claude --resume <session id>` from the output, or to the log path.
