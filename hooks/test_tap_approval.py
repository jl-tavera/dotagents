"""tap-approval.py and reserved-skills.py, driven the way Claude Code drives them: JSON on stdin.

    python .claude/hooks/test_tap_approval.py
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

HOOKS = Path(__file__).resolve().parent


class TapApprovalTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.project = self.root
        for skill, frontmatter in (("ship", "approval: tap"), ("tdd", "description: x")):
            (self.root / ".claude" / "skills" / skill).mkdir(parents=True)
            (self.root / ".claude" / "skills" / skill / "SKILL.md").write_text(f"---\nname: {skill}\n{frontmatter}\n---\n")
        self.session = f"test-{uuid.uuid4().hex}"
        self.addCleanup(lambda: Path(tempfile.gettempdir(), f"claude-tap-approval-{self.session}.json").unlink(missing_ok=True))

    def hook(self, script: str, payload: dict) -> int:
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.project), "HOME": str(self.root), "USERPROFILE": str(self.root)}
        return subprocess.run([sys.executable, str(HOOKS / script)], input=json.dumps(payload),
                              text=True, capture_output=True, env=env).returncode

    def tap(self, label: str, session: str | None = None) -> int:
        return self.hook("tap-approval.py", {
            "hook_event_name": "PostToolUse", "tool_name": "AskUserQuestion", "session_id": session or self.session,
            "tool_response": {"questions": [], "answers": {"Ship it?": label}}})

    def call(self, skill: str) -> int:
        return self.hook("tap-approval.py", {
            "hook_event_name": "PreToolUse", "tool_name": "Skill", "session_id": self.session,
            "tool_input": {"skill": skill}})

    def test_ship_needs_a_tap_and_the_tap_is_used_up(self):
        self.assertEqual(self.call("ship"), 2)
        self.assertEqual(self.tap("Ship it — run /ship"), 0)
        self.assertEqual(self.call("ship"), 0)
        self.assertEqual(self.call("ship"), 2)

    def test_the_latest_answer_decides(self):
        self.tap("Ship it — run /ship")
        self.tap("Not yet")
        self.assertEqual(self.call("ship"), 2)

    def test_a_tap_in_another_session_does_not_count(self):
        self.tap("Ship it — run /ship", session=f"other-{uuid.uuid4().hex}")
        self.assertEqual(self.call("ship"), 2)

    def test_skills_without_approval_tap_are_untouched(self):
        self.assertEqual(self.call("tdd"), 0)

    def test_ship_skill_md_still_cannot_be_read(self):
        read = {"tool_name": "Read", "tool_input": {"file_path": str(self.root / ".claude/skills/ship/SKILL.md")}}
        self.assertEqual(self.hook("reserved-skills.py", read), 2)

    def test_user_level_skills_count_when_the_project_has_none(self):
        empty = tempfile.TemporaryDirectory()
        self.addCleanup(empty.cleanup)
        self.project = Path(empty.name)
        self.assertEqual(self.call("ship"), 2)
        self.assertEqual(self.tap("Ship it — run /ship"), 0)
        self.assertEqual(self.call("ship"), 0)


if __name__ == "__main__":
    unittest.main()
