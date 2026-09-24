#!/usr/bin/env python3
"""Link this repo into each harness's user-level config. Safe to re-run.

    python install.py

Claude Code  ~/.claude/skills/<name>, ~/.claude/hooks, ~/.claude/CLAUDE.md (@-imports AGENTS.md),
             and the wiring in harness/claude/hooks.json merged into ~/.claude/settings.json
Shared       ~/.agents/skills/<name> (Codex and other Agent Skills harnesses), ~/.codex/AGENTS.md

Links are junctions on Windows (no admin needed) and symlinks elsewhere. Anything already at a
path that is not a link to this repo is left alone and reported.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent
HOME = Path.home()


def link(path: Path, target: Path) -> None:
    if path.exists() or path.is_symlink():
        if path.resolve() == target.resolve():
            return
        print(f"skip  {path} (exists, not ours)")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt" and target.is_dir():
        subprocess.run(["cmd", "/c", "mklink", "/J", str(path), str(target)], check=True, capture_output=True)
    else:
        try:
            path.symlink_to(target, target_is_directory=target.is_dir())
        except OSError:  # a file symlink on Windows without Developer Mode
            print(f"fail  {path}: turn on Windows Developer Mode, or copy {target} there")
            return
    print(f"link  {path} -> {target}")


def merge_hooks(settings_path: Path, hooks_dir: Path) -> None:
    wiring = (REPO / "harness" / "claude" / "hooks.json").read_text(encoding="utf-8")
    wiring = json.loads(wiring.replace("{HOOKS}", hooks_dir.as_posix()))
    settings = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
    hooks = settings.setdefault("hooks", {})
    added = 0
    for event, entries in wiring.items():
        have = {h["command"] for e in hooks.get(event, []) for h in e.get("hooks", [])}
        for entry in entries:
            if not {h["command"] for h in entry["hooks"]} <= have:
                hooks.setdefault(event, []).append(entry)
                added += 1
    if not added:
        return
    if settings_path.exists():
        shutil.copy2(settings_path, settings_path.with_name(f"settings.json.bak-{date.today():%Y%m%d}"))
    settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"hooks {settings_path}: {added} added")


def main() -> int:
    claude = HOME / ".claude"
    for skill in sorted(p for p in (REPO / "skills").iterdir() if (p / "SKILL.md").exists()):
        link(claude / "skills" / skill.name, skill)
        link(HOME / ".agents" / "skills" / skill.name, skill)
    link(claude / "hooks", REPO / "hooks")
    link(HOME / ".codex" / "AGENTS.md", REPO / "AGENTS.md")

    claude_md = claude / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text(f"@{(REPO / 'AGENTS.md').as_posix()}\n", encoding="utf-8")
        print(f"write {claude_md}")

    merge_hooks(claude / "settings.json", claude / "hooks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
