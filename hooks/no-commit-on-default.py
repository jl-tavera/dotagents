#!/usr/bin/env python3
"""Refuse `git commit` and `git push` while HEAD is the default branch.

A PreToolUse hook on the Bash tool. It exists because an instruction is not
enough: `/implement` used to end with "Commit your work to the current branch",
and that one sentence was enough to put a whole ticket onto `main`. Wording can
be overridden by the next thing that is said. This cannot.

The blocking contract, which is asymmetric and worth stating:

    exit 0   allow, and stdout/stderr are not shown to anyone
    exit 2   BLOCK, and stderr is shown to the model
    other    the tool RUNS ANYWAY, and stderr is shown only to the user

So the last case is not an error path. It is the one to use when this hook is
broken but blocking every shell command would be worse than the thing it guards
against.

Written in Python rather than the shell because `jq` is not installed on this
machine. The bundled `git-guardrails-claude-code` script pipes stdin through
`jq`, so on this machine its command variable comes back empty, nothing matches,
and it exits 0 -- protection that is not there and does not say so.
"""

import json
import os
import re
import shlex
import subprocess
import sys

# Branches this refuses to commit to. `origin/HEAD` is consulted first, but it
# is unset in this clone -- `git symbolic-ref refs/remotes/origin/HEAD` fails --
# so these are what it actually falls back to, and they are the answer for every
# repository anyone here is likely to open.
FALLBACK_PROTECTED = {"main", "master"}

# The subcommands that write history somewhere it is hard to take back.
GUARDED = {"commit", "push"}

# git's own options that swallow the next word. Without these, `git -C /tmp push`
# reads as subcommand `/tmp` and slips through -- which it did, until a test said so.
VALUED_GLOBALS = {
    "-C",
    "-c",
    "--git-dir",
    "--work-tree",
    "--namespace",
    "--exec-path",
    "--super-prefix",
}

# Say this in the command and it goes through. A guard with no way past it is one
# people turn off entirely the first time it is wrong, and then it guards nothing.
OVERRIDE = "#allow-on-default"


def subcommand_of(segment: str) -> str | None:
    """The git subcommand a single shell segment invokes, or None.

    Parsed rather than matched. `grep -qE "git push"` -- what the bundled script
    does -- also fires on `echo 'remember to git push later'` and on
    `grep -r "git push" docs/`, because a mention inside quotes looks exactly
    like an invocation to a substring search.
    """
    try:
        argv = shlex.split(segment.strip())
    except ValueError:
        # Unbalanced quotes: this segment is not something we can read honestly.
        return None

    at = 0

    # Step over `FOO=bar git ...`.
    while at < len(argv) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[at]):
        at += 1

    if at >= len(argv) or not argv[at].endswith("git"):
        return None

    at += 1
    while at < len(argv):
        word = argv[at]
        if word in VALUED_GLOBALS:
            at += 2
            continue
        if word.startswith("-"):
            at += 1
            continue
        return word

    return None


def guarded_subcommand(command: str) -> str | None:
    """The first guarded git subcommand in a whole command line, or None."""
    for segment in re.split(r"&&|\|\||;|\||\n", command):
        found = subcommand_of(segment)
        if found in GUARDED:
            return found
    return None


def current_branch(cwd: str) -> str | None:
    """The branch HEAD is on, or None -- detached, not a repository, or no git."""
    try:
        done = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if done.returncode != 0:
        return None

    branch = done.stdout.strip()
    return None if branch in ("", "HEAD") else branch


def protected_branches(cwd: str) -> set[str]:
    """What `origin/HEAD` names, plus the fallback. A superset on purpose."""
    protected = set(FALLBACK_PROTECTED)

    try:
        done = subprocess.run(
            ["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if done.returncode == 0:
            named = done.stdout.strip()
            if named.startswith("origin/"):
                protected.add(named[len("origin/") :])
    except (OSError, subprocess.SubprocessError):
        pass

    return protected


def allow() -> None:
    sys.exit(0)


def block(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)


def warn_but_allow(message: str) -> None:
    """This hook could not do its job, and saying so beats either alternative.

    Not exit 2: a payload shape this cannot read would block every shell command
    in the session, and the only way out would be editing settings. Not exit 0
    either, which shows nobody anything -- that is the silent failure this file
    exists to avoid.
    """
    print(f"[no-commit-on-default] {message}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    raw = sys.stdin.read()

    try:
        payload = json.loads(raw)
        command = payload["tool_input"]["command"]
    except (json.JSONDecodeError, KeyError, TypeError):
        warn_but_allow(
            "could not read the hook payload, so this command was not checked. "
            "The guard against committing to the default branch is not working."
        )
        return

    if not isinstance(command, str):
        warn_but_allow("the hook payload carried no command; nothing was checked.")
        return

    if OVERRIDE in command:
        allow()

    subcommand = guarded_subcommand(command)
    if subcommand is None:
        allow()

    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    branch = current_branch(cwd)

    if branch is None:
        # Failing closed, and only here. We already know this command writes
        # history; not knowing where is exactly when to stop.
        block(
            f"Refused: `git {subcommand}` was asked for, and the current branch "
            f"could not be determined in {cwd}.\n"
            f"If this is deliberate, re-run the command with {OVERRIDE} in it."
        )
        return

    if branch not in protected_branches(cwd):
        allow()

    block(
        f"Refused: you are on '{branch}', which is the default branch.\n"
        f"\n"
        f"Branch before committing:  git switch -c <type>/<issue>-<slug>\n"
        f"  for example:             git switch -c feat/35-mirror-and-add\n"
        f"\n"
        f"Then commit, and use /ship to push, open a PR and land it.\n"
        f"Deliberate? Re-run the command with {OVERRIDE} in it."
    )


if __name__ == "__main__":
    main()
