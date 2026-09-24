#!/usr/bin/env python3
"""Refuse to open the instructions of a skill reserved for the user to invoke.

A PreToolUse hook on Bash, Read and Grep. It guards the gap the Skill tool
already closes from one side: a skill whose frontmatter says
`disable-model-invocation: true` cannot be called through that tool, and the
refusal says so. Nothing stopped the model reading `SKILL.md` with `cat` and
then carrying out the steps by hand, which is the same workflow arriving by a
door with no lock on it.

That is not hypothetical. `/ship` was hand-executed this way -- preflight,
commits, push, PR, merge -- and the one instruction its author had written down
that the model disagreed with (`Closes #N`) was quietly substituted on the way
past. A workflow reserved for a person is reserved so the person decides when it
runs and what it does. Replicating it takes both of those away, and the model
had no reason to notice it was doing so.

The blocking contract, inherited from `no-commit-on-default.py` and asymmetric
in the same way:

    exit 0   allow, and stdout/stderr are not shown to anyone
    exit 2   BLOCK, and stderr is shown to the model
    other    the tool RUNS ANYWAY, and stderr is shown only to the user

The last case is not an error path. It is what to do when this hook is broken
and blocking every read in the session would be worse than the thing it guards.

Reading is blocked rather than the actions a workflow performs, because the
actions are ordinary on their own. `gh pr merge` is correct when a person asked
for it and wrong when a skill's steps are being replayed, and no hook can tell
those apart from the command. The instructions are where the difference lives.
"""

import json
import os
import re
import sys

# Say this in the command and it goes through. Some reads are legitimate -- a
# review gathering this repo's documented standards has honest business in
# `.claude/skills/` -- and a guard with no way past it is one that gets removed
# the first time it is wrong, after which it guards nothing.
OVERRIDE = "#reading-not-running"

# `.claude/skills/<name>/SKILL.md`, however it is spelled: either slash, with or
# without the leading `.claude/`, quoted or bare.
SKILL_PATH = re.compile(
    r"""(?:\.claude[/\\])?skills[/\\]([A-Za-z0-9._-]+)[/\\]SKILL\.md""",
    re.IGNORECASE,
)

# `approval: tap` reserves a skill too: tap-approval.py lets the Skill tool start it right
# after the user taps an option naming it, and reading its steps to replay them by hand would
# walk around that tap the same way.
FRONTMATTER_FLAG = re.compile(
    r"^\s*(?:disable-model-invocation\s*:\s*true|approval\s*:\s*tap)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def claude_file(root: str, *parts: str) -> str:
    """`.claude/<parts>` in the project if it is there, else the user-level `~/.claude/<parts>`."""
    path = os.path.join(root, ".claude", *parts)
    return path if os.path.exists(path) else os.path.join(os.path.expanduser("~"), ".claude", *parts)


def reserved(root: str, skill: str) -> bool:
    """Whether `skill`'s frontmatter reserves it for the user.

    Read from the file rather than from a list kept here. A list would be a
    second copy of a fact the skill already states, and would go stale the first
    time somebody adds a skill without knowing this hook exists.
    """
    path = claude_file(root, "skills", skill, "SKILL.md")

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            # The frontmatter only. Enough of the file to hold it, and not so
            # much that a long skill is read into memory to answer a yes or no.
            head = handle.read(4096)
    except OSError:
        # Cannot read it, so cannot claim it is reserved. The Skill tool still
        # refuses model invocation on its own, which is the guard this one only
        # adds a second door to.
        return False

    return bool(FRONTMATTER_FLAG.search(head))


def named_in(text: str) -> list[str]:
    """Every skill whose SKILL.md this text refers to, in order, without repeats."""
    found: list[str] = []

    for match in SKILL_PATH.finditer(text):
        skill = match.group(1)
        if skill not in found:
            found.append(skill)

    return found


def subject_of(payload: dict) -> str | None:
    """The text to inspect, whichever tool this is.

    Bash carries a command line; Read a path; Grep a path and a glob. All three
    can put the bytes of a SKILL.md in front of the model, so all three are
    read the same way: as text that may name one.
    """
    tool = payload.get("tool_name")
    supplied = payload.get("tool_input")

    if not isinstance(supplied, dict):
        return None

    if tool == "Bash":
        command = supplied.get("command")
        return command if isinstance(command, str) else None

    if tool in ("Read", "Grep"):
        parts = [supplied.get("file_path"), supplied.get("path"), supplied.get("glob")]
        return "\n".join(part for part in parts if isinstance(part, str))

    return None


def allow() -> None:
    sys.exit(0)


def block(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)


def warn_but_allow(message: str) -> None:
    """This hook could not do its job, and saying so beats either alternative."""
    print(f"[reserved-skills] {message}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    raw = sys.stdin.read()

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        warn_but_allow(
            "could not read the hook payload, so this was not checked. "
            "The guard against replaying a reserved skill is not working."
        )
        return

    if not isinstance(payload, dict):
        warn_but_allow("the hook payload was not an object; nothing was checked.")
        return

    subject = subject_of(payload)
    if not subject:
        allow()

    if OVERRIDE in subject:
        allow()

    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    for skill in named_in(subject):
        if not reserved(root, skill):
            continue

        block(
            f"Refused: `{skill}` is reserved for the user to invoke, and this "
            f"would open its instructions.\n"
            f"\n"
            f"Its frontmatter reserves it for the user (`disable-model-invocation: "
            f"true`, or `approval: tap` -- startable only right after the user taps "
            f"an option naming it), and reading the steps to carry them out by hand "
            f"is the same thing through a different door -- it takes away both the "
            f"decision to run it and, in practice, the parts of it you would have "
            f"kept.\n"
            f"\n"
            f"Do not replicate it. Stop, say what you need, and ask the user with "
            f"AskUserQuestion to run /{skill}.\n"
            f"\n"
            f"Genuinely only reading -- quoting the file, auditing it, editing "
            f"it? Re-run with {OVERRIDE} in the command or path."
        )

    allow()


if __name__ == "__main__":
    main()
