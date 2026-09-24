#!/usr/bin/env python3
"""Inject the /lazy ruleset into every session and every sub-agent.

A SessionStart + SubagentStart hook. SessionStart takes plain stdout as
context; SubagentStart takes JSON with hookSpecificOutput.additionalContext.
The intensity comes from `.claude/lazy-mode`, the project's or else ~/.claude's (lite | full | ultra | off);
`off` prints nothing. Anything unexpected exits 0 silently -- a broken hook
must never cost the session.
"""

import json
import os
import re
import sys

MODES = {"lite", "full", "ultra", "off"}


def claude_file(root: str, *parts: str) -> str:
    """`.claude/<parts>` in the project if it is there, else the user-level `~/.claude/<parts>`."""
    path = os.path.join(root, ".claude", *parts)
    return path if os.path.exists(path) else os.path.join(os.path.expanduser("~"), ".claude", *parts)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    event = payload.get("hook_event_name", "SessionStart")
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    try:
        with open(claude_file(root, "lazy-mode"), encoding="utf-8") as f:
            mode = f.read().strip().lower()
    except OSError:
        mode = "full"
    if mode not in MODES:
        mode = "full"
    if mode == "off":
        return 0

    try:
        with open(claude_file(root, "skills", "lazy", "SKILL.md"), encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return 0
    body = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S).strip()
    context = f"lazy mode: {mode} — `/lazy lite|full|ultra|off` to change.\n\n{body}"

    if event == "SubagentStart":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": context}}))
    else:
        print(context)
    return 0


if __name__ == "__main__":
    sys.exit(main())
