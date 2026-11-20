"""SQL for the `medication_reminders_sent` dedupe table."""

from core import db


def was_sent(schedule_id, reminder_time, sent_date):
    return db.query_value(
        """
        SELECT COUNT(*) FROM medication_reminders_sent
         WHERE medication_schedule_id = ? AND reminder_time = ? AND sent_date = ?
        """,
        (schedule_id, reminder_time, sent_date),
        default=0,
    ) > 0


def mark_sent(schedule_id, reminder_time, sent_date):
    db.execute(
        """
        INSERT OR IGNORE INTO medication_reminders_sent
            (medication_schedule_id, reminder_time, sent_date)
        VALUES (?, ?, ?)
        """,
        (schedule_id, reminder_time, sent_date),
    )
