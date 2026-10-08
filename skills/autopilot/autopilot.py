#!/usr/bin/env python3
"""Run /build <n> auto for each ticket, one fresh headless session at a time, until one stops.

    python autopilot.py              every open `ready-for-agent` ticket
    python autopilot.py 51-55 58     a range and/or single numbers
    python autopilot.py --max 3 ...  at most three tickets

Run it from the project's root. Each ticket gets its own `claude -p` session with
CLAUDE_AUTOPILOT=1 in its env -- the only thing that lets tap-approval.py start /ship without a
tap, and something the model inside cannot set for itself. The session loads user and local
settings only, so only the user-level hooks guard it (see run()). Prints one line per milestone,
flushed, so whoever runs it (a person or the /autopilot chat) can follow along.

Logs and the STOP file live in the temp dir, never in the repo: an untracked file there would
make /ship's "tree is not what you expected" check stop every run.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

LABEL = "ready-for-agent"
STUCK = "needs-human"


def say(line: str) -> None:
    print(line, flush=True)


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8").stdout.strip()


def parse(argv: list[str]) -> tuple[list[int], int | None]:
    # The /autopilot chat passes the user's words as typed: `52 and 53`, `52, 53`.
    numbers, limit, rest = [], None, iter(" ".join(argv).replace(",", " ").split())
    for arg in rest:
        if arg.lower() == "and":
            continue
        if arg == "--max":
            limit = int(next(rest))
        elif "-" in arg:
            low, high = map(int, arg.lstrip("#").split("-"))
            numbers += range(low, high + 1)
        else:
            numbers.append(int(arg.lstrip("#")))
    return sorted(set(numbers)), limit


def ticket(n: int) -> dict:
    out = gh("issue", "view", str(n), "--json", "state,labels,title")
    if not out:
        return {"state": "MISSING", "labels": [], "title": ""}
    data = json.loads(out)
    data["labels"] = [label["name"] for label in data["labels"]]
    return data


def blocked(repo: str, n: int) -> bool:
    # Native dependency links, as /issues creates them. No API (or an error) reads as unblocked.
    out = gh("api", f"repos/{repo}/issues/{n}/dependencies/blocked_by",
             "--jq", '[.[] | select(.state == "open")] | length')
    return out.isdigit() and int(out) > 0


def milestone(event: dict) -> str | None:
    """A one-line summary of a stream-json event worth showing, or None."""
    if event.get("type") != "assistant":
        return None
    for block in event.get("message", {}).get("content", []):
        if block.get("type") != "tool_use":
            continue
        tool, args = block.get("name"), block.get("input", {})
        if tool == "Skill":
            return f"/{args.get('skill')}"
        command = args.get("command", "") if tool == "Bash" else ""
        for needle, text in ((STUCK, "flagged needs-human"), ("gh issue comment", "commented on the ticket"),
                             ("gh pr create", "opening PR"), ("gh pr merge", "merging"),
                             ("git switch -c", "branched"), ("git push", "pushing")):
            if needle in command:
                return text
    return None


def run(n: int, logs: str, claude: str) -> None:
    log_path = os.path.join(logs, f"{n}.log")
    env = {**os.environ, "CLAUDE_AUTOPILOT": "1"}
    # No `project` source: repos that vendored an old copy of these hooks wire it in their
    # .claude/settings.json, and that copy refuses /ship even with CLAUDE_AUTOPILOT set.
    # lazy: drops a repo's own settings.json (permissions, env) too; load `project` again once no repo vendors hooks.
    command = [claude, "-p", f"/build {n} auto", "--setting-sources", "user,local", "--permission-mode", "auto",
               "--output-format", "stream-json", "--verbose"]
    with open(log_path, "w", encoding="utf-8") as log, subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", env=env) as proc:
        for line in proc.stdout:
            log.write(line)
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "system" and event.get("subtype") == "init":
                say(f"#{n} session {event.get('session_id')}  (claude --resume {event.get('session_id')})")
            elif event.get("type") == "result":
                cost = event.get("total_cost_usd")
                say(f"#{n} session ended{f' (${cost:.2f})' if cost else ''}: {str(event.get('result', ''))[-300:]}")
            elif text := milestone(event):
                say(f"#{n} {text}")
    say(f"#{n} log: {log_path}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows pipes default to cp1252
    try:
        numbers, limit = parse(sys.argv[1:])
    except (ValueError, StopIteration):
        say(f"STOPPED: can't read {' '.join(sys.argv[1:])!r}; use numbers, ranges (51-55) and --max N")
        return 1
    claude = shutil.which("claude")
    if not claude:
        say("STOPPED: `claude` is not on PATH")
        return 1
    repo = gh("repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")
    if not repo:
        say("STOPPED: not in a GitHub repo, or `gh` is not logged in")
        return 1
    if not numbers:
        out = gh("issue", "list", "--label", LABEL, "--state", "open", "--limit", "200", "--json", "number")
        numbers = sorted(issue["number"] for issue in json.loads(out or "[]"))

    logs = os.path.join(tempfile.gettempdir(), "claude-autopilot", repo.replace("/", "-"))
    os.makedirs(logs, exist_ok=True)
    stop_file = os.path.join(logs, "STOP")
    if os.path.exists(stop_file):
        os.remove(stop_file)
    say(f"autopilot {repo}: {', '.join(f'#{n}' for n in numbers) or 'nothing to do'}")
    say(f"stop after the current ticket: create {stop_file}")

    done, pending = 0, list(numbers)
    while pending and (limit is None or done < limit):
        if os.path.exists(stop_file):
            say(f"STOPPED on request. Left: {', '.join(f'#{n}' for n in pending)}")
            return 0
        runnable = None
        for n in list(pending):
            info = ticket(n)
            if info["state"] != "OPEN":
                say(f"#{n} skipped ({info['state'].lower()})")
                pending.remove(n)
            elif STUCK in info["labels"]:
                say(f"#{n} skipped (labelled {STUCK})")
                pending.remove(n)
            elif not blocked(repo, n):
                runnable = n
                break
        if runnable is None:
            if pending:
                say(f"STOPPED: every remaining ticket is blocked: {', '.join(f'#{n}' for n in pending)}")
                return 1
            break

        info = ticket(runnable)
        say(f"#{runnable} started: {info['title']}")
        run(runnable, logs, claude)
        after = ticket(runnable)
        if after["state"] != "CLOSED":
            reason = "labelled needs-human, see the ticket" if STUCK in after["labels"] else "ticket still open"
            say(f"#{runnable} STOPPED: {reason}")
            return 1
        say(f"#{runnable} merged ✓")
        pending.remove(runnable)
        done += 1

    say(f"autopilot done: {done} merged" + (f", left: {', '.join(f'#{n}' for n in pending)}" if pending else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
