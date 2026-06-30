import os
import tempfile
import unittest
from datetime import datetime, timedelta

import database
import logic


class LogicRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "worktime_test.db")
        database._resolved_db_path = self.db_path
        database.init_db()

    def tearDown(self):
        database._resolved_db_path = None
        self.temp_dir.cleanup()

    def add_user(self, name="Tester"):
        result = logic.add_user(name)
        self.assertEqual(result["status"], "success")
        return result["user_id"]

    def test_late_night_break_time_matches_swrs_examples(self):
        self.assertEqual(logic.calculate_work_time("08:30", "17:30", 0), (480, 60))
        self.assertEqual(logic.calculate_work_time("08:30", "22:00", 0), (720, 90))
        self.assertEqual(logic.calculate_work_time("08:30", "02:00", 0), (930, 120))

    def test_weekend_replacement_leave_does_not_earn_overtime(self):
        user_id = self.add_user()
        weekend = "2026-06-27"
        self.assertGreaterEqual(datetime.strptime(weekend, "%Y-%m-%d").weekday(), 5)

        logic.save_work_log(user_id, weekend, "replacement_leave", "", "", 0, 0, "")
        log = logic.get_work_logs(user_id, weekend, weekend)[0]

        self.assertEqual(log["overtime_earned"], 0)
        self.assertEqual(log["overtime_used"], 480)

    def test_monthly_summary_reports_overtime_expiring_within_7_days(self):
        user_id = self.add_user()
        today = datetime.today()
        earned_date = (today - timedelta(days=10)).strftime("%Y-%m-%d")
        expires_at = (today + timedelta(days=3)).strftime("%Y-%m-%d")
        month_str = today.strftime("%Y-%m")

        conn = database.get_connection()
        c = conn.cursor()
        c.execute(
            """
            INSERT INTO work_logs
            (user_id, date, type, clock_in, clock_out, work_time, overtime_earned, overtime_used)
            VALUES (?, ?, 'normal', '08:30', '18:30', 540, 60, 0)
            """,
            (user_id, earned_date),
        )
        c.execute(
            """
            INSERT INTO overtime_vault
            (user_id, date, earned_minutes, used_minutes, expires_at, is_extended)
            VALUES (?, ?, 60, 0, ?, 0)
            """,
            (user_id, earned_date, expires_at),
        )
        conn.commit()
        conn.close()

        summary = logic.get_monthly_summary(user_id, month_str)
        self.assertEqual(summary["expiring_soon"], 60)

    def test_sync_vault_removes_stale_earned_rows(self):
        user_id = self.add_user()
        work_date = "2026-06-15"

        logic.save_work_log(user_id, work_date, "normal", "08:30", "19:00", 0, 0, "")
        logic.sync_vault(user_id)

        conn = database.get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM overtime_vault WHERE user_id = ?", (user_id,))
        self.assertEqual(c.fetchone()[0], 1)

        c.execute("UPDATE work_logs SET work_time = 480, overtime_earned = 0 WHERE user_id = ? AND date = ?", (user_id, work_date))
        conn.commit()
        conn.close()

        logic.sync_vault(user_id)

        conn = database.get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM overtime_vault WHERE user_id = ?", (user_id,))
        self.assertEqual(c.fetchone()[0], 0)
        conn.close()


if __name__ == "__main__":
    unittest.main()
