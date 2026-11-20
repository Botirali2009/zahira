"""SQL for the `motivation_log` dedupe table."""

from core import db


def was_sent_today(patient_id, sent_date):
    return db.query_value(
        "SELECT COUNT(*) FROM motivation_log WHERE patient_id = ? AND sent_date = ?",
        (patient_id, sent_date),
        default=0,
    ) > 0


def mark_sent(patient_id, sent_date, reason):
    db.execute(
        "INSERT OR IGNORE INTO motivation_log (patient_id, sent_date, reason) VALUES (?, ?, ?)",
        (patient_id, sent_date, reason),
    )
