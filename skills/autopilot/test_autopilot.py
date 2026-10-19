#!/usr/bin/env python3
"""python skills/autopilot/test_autopilot.py -- the launch gate and the flag parsing, nothing that needs gh or git."""

import unittest

import autopilot

RUNNING = {51: object()}


class Headroom(unittest.TestCase):
    def test_nothing_running_always_starts_one(self):
        self.assertTrue(autopilot.headroom({"five_hour": 0.95, "seven_day": 0.1}, None, set(), {}))

    def test_waits_for_the_newest_session_to_report(self):
        self.assertFalse(autopilot.headroom({"five_hour": None, "seven_day": None}, 51, set(), RUNNING))

    def test_no_reading_counts_as_headroom_once_reported(self):
        self.assertTrue(autopilot.headroom({"five_hour": None, "seven_day": None}, 51, {51}, RUNNING))

    def test_holds_at_the_ceiling(self):
        self.assertFalse(autopilot.headroom({"five_hour": 0.85, "seven_day": 0.2}, 51, {51}, RUNNING))

    def test_starts_under_the_ceiling(self):
        self.assertTrue(autopilot.headroom({"five_hour": 0.5, "seven_day": 0.79}, 51, {51}, RUNNING))


class Parse(unittest.TestCase):
    def test_serial_range_and_max(self):
        self.assertEqual(autopilot.parse(["--serial", "51-55,", "58", "--max", "2"]),
                         ([51, 52, 53, 54, 55, 58], 2, 1, autopilot.MODEL))

    def test_default_is_parallel_on_opus(self):
        self.assertEqual(autopilot.parse(["52 and 53"]), ([52, 53], None, autopilot.MAX_JOBS, autopilot.MODEL))

    def test_jobs_sets_the_ceiling(self):
        self.assertEqual(autopilot.parse(["--jobs", "2", "51"]), ([51], None, 2, autopilot.MODEL))
        with self.assertRaises(ValueError):
            autopilot.parse(["--jobs", "0", "51"])

    def test_model_is_passed_as_typed(self):
        self.assertEqual(autopilot.parse(["--model", "sonnet", "51"]), ([51], None, autopilot.MAX_JOBS, "sonnet"))


class Standing(unittest.TestCase):
    def test_reports_gone_off_and_unpushed(self):
        lines = ["main\torigin/main\t", "feat/a\torigin/feat/a\t[gone]",
                 "feat/b\torigin/feat/b\t[ahead 2, behind 1]", "scratch"]  # last line: git() stripped its tabs
        self.assertEqual(autopilot.standing(lines), [
            "sync: upstream gone for feat/a -- `git branch -D <name>` once nothing there is wanted",
            "sync: not level with upstream: feat/b [ahead 2, behind 1]",
            "sync: never pushed: scratch"])

    def test_level_branches_say_nothing(self):
        self.assertEqual(autopilot.standing(["main\torigin/main"]), [])


if __name__ == "__main__":
    unittest.main()
