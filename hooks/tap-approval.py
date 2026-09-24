#!/usr/bin/env python3
"""Let the user's tap on a question start a skill they reserve -- and nothing else.

A PostToolUse hook on AskUserQuestion and a PreToolUse hook on Skill. A skill whose
frontmatter says `approval: tap` (today: ship) is callable through the Skill tool, but only
straight after the user tapped an option that names it -- `Ship it — run /ship`. The tap is
the user deciding; this hook is what keeps it their decision rather than a sentence the model
could talk itself past, the same reason `reserved-skills.py` exists.

    PostToolUse(AskUserQuestion)  the latest answer replaces the pass: it holds exactly the
                                  `approval: tap` skills named in the options the user chose
                                  (so a later "Not yet" withdraws an earlier "Ship it")
    PreToolUse(Skill)             such a skill goes through only on a pass for this session,
                                  under 15 minutes old, which the call uses up

The pass is a file in the system temp dir keyed by session id: nothing lands in the repo.

Exit codes as in `reserved-skills.py`: 0 allow, 2 block (stderr to the model), anything else
the tool runs anyway and stderr reaches the user. A guard that cannot read its input fails
closed for the pass -- no pass is written -- and says so, rather than blocking every tool.
"""

import json
import os
import re
import sys
import tempfile
import time

APPROVAL = re.compile(r"^\s*approval\s*:\s*tap\s*$", re.IGNORECASE | re.MULTILINE)
# `/ship` in "Ship it — run /ship", but not the `/check` inside `contracts/check.py`.
NAMED = re.compile(r"(?<![\w/])/([A-Za-z0-9][A-Za-z0-9._-]*)")
MAX_AGE_SECONDS = 15 * 60


def claude_file(root: str, *parts: str) -> str:
    """`.claude/<parts>` in the project if it is there, else the user-level `~/.claude/<parts>`."""
    path = os.path.join(root, ".claude", *parts)
    return path if os.path.exists(path) else os.path.join(os.path.expanduser("~"), ".claude", *parts)


def tap_only(root: str, skill: str) -> bool:
    """Whether `skill`'s frontmatter says `approval: tap`. Read from the file, not a list here."""
    path = claude_file(root, "skills", skill, "SKILL.md")
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return bool(APPROVAL.search(handle.read(4096)))
    except OSError:
        return False


def pass_path(session: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session or "no-session")
    return os.path.join(tempfile.gettempdir(), f"claude-tap-approval-{safe}.json")


def chosen_answers(payload: dict) -> list[str] | None:
    """The labels the user picked, or None when the payload is not a shape this knows."""
    for source in (payload.get("tool_response"), payload.get("tool_input")):
        if isinstance(source, dict) and isinstance(source.get("answers"), dict):
            return [str(value) for value in source["answers"].values()]
    return None


def on_answer(payload: dict, root: str) -> None:
    answers = chosen_answers(payload)
    target = pass_path(payload.get("session_id", ""))
    if answers is None:
        _remove(target)
        warn("could not read which options were tapped, so no tap can start a skill this time. "
             "Type the slash command instead.")
    skills = sorted({name for label in answers for name in NAMED.findall(label) if tap_only(root, name)})
    if not skills:
        _remove(target)
        sys.exit(0)
    with open(target, "w", encoding="utf-8") as handle:
        json.dump({"at": time.time(), "skills": skills}, handle)
    sys.exit(0)


def on_skill(payload: dict, root: str) -> None:
    supplied = payload.get("tool_input")
    raw = supplied.get("skill") if isinstance(supplied, dict) else None
    skill = str(raw or "").lstrip("/").split(":")[-1]
    if not skill or not tap_only(root, skill):
        sys.exit(0)

    target = pass_path(payload.get("session_id", ""))
    try:
        with open(target, "r", encoding="utf-8") as handle:
            granted = json.load(handle)
    except (OSError, ValueError):
        granted = {}
    fresh = time.time() - float(granted.get("at", 0)) < MAX_AGE_SECONDS
    if fresh and skill in granted.get("skills", []):
        _remove(target)
        sys.exit(0)

    print(
        f"Refused: /{skill} starts only on the user's tap.\n"
        f"\n"
        f"Its frontmatter says `approval: tap`: it runs when the user types /{skill}, or right after "
        f"they tap an AskUserQuestion option that names it (\"Ship it — run /{skill}\"). No such tap "
        f"is on record for this session in the last 15 minutes.\n"
        f"\n"
        f"Ask with AskUserQuestion, and call it only if they choose that option.",
        file=sys.stderr,
    )
    sys.exit(2)


def _remove(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def warn(message: str) -> None:
    print(f"[tap-approval] {message}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        warn("could not read the hook payload; nothing was checked.")
    if not isinstance(payload, dict):
        warn("the hook payload was not an object; nothing was checked.")

    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    tool = payload.get("tool_name")
    if payload.get("hook_event_name") == "PostToolUse" and tool == "AskUserQuestion":
        on_answer(payload, root)
    if payload.get("hook_event_name") == "PreToolUse" and tool == "Skill":
        on_skill(payload, root)
    sys.exit(0)


if __name__ == "__main__":
    main()
