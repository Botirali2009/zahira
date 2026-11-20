"""Detects "it's time for this dose" and announces it — nothing here sends a
notification itself. `check_due_reminders()` is the pure, testable part:
scan active schedules, compare the current local HH:MM against each one's
`times_json`, and `events.emit(MEDICATION_REMINDER_DUE, ...)` for whichever
slot just came due. `hooks/medication_reminder_hooks.py` is what turns that
into an actual push — deleting that file stops reminders from notifying
without touching this file, same as every other event in the app.

`run_forever()` is a daemon thread started only from `app.py`'s
`if __name__ == "__main__":` block — never during tests, never on import —
so importing this module or calling `create_app()` never spawns a
background thread by accident.
"""

import json
import threading
import time
from datetime import datetime

from config import features
from core import events
from repos import medication_reminder_repo, medication_repo

TICK_SECONDS = 60


def _within_date_range(schedule, today):
    if schedule["start_date"] and today < schedule["start_date"]:
        return False
    if schedule["end_date"] and today > schedule["end_date"]:
        return False
    return True


def check_due_reminders(now=None):
    """Runs one scan; returns how many reminders were emitted (tests call
    this directly instead of waiting on the background thread)."""
    if not features.enabled("medication_reminders"):
        return 0

    now = now or datetime.now()
    current_time = now.strftime("%H:%M")
    today = now.strftime("%Y-%m-%d")

    fired = 0
    for schedule in medication_repo.list_active():
        if not _within_date_range(schedule, today):
            continue
        try:
            times = json.loads(schedule["times_json"] or "[]")
        except (TypeError, ValueError):
            continue
        if current_time not in times:
            continue
        if medication_reminder_repo.was_sent(schedule["id"], current_time, today):
            continue

        medication_reminder_repo.mark_sent(schedule["id"], current_time, today)
        events.emit(
            events.MEDICATION_REMINDER_DUE,
            patient_id=schedule["patient_id"],
            medication_schedule_id=schedule["id"],
            drug_name=schedule["drug_name"],
            time=current_time,
        )
        fired += 1
    return fired


def run_forever(app):
    """Blocks forever; call this from a daemon thread only."""
    while True:
        try:
            with app.app_context():
                check_due_reminders()
        except Exception:
            app.logger.exception("medication reminder scheduler tick failed")
        time.sleep(TICK_SECONDS)


def start_background_thread(app):
    thread = threading.Thread(target=run_forever, args=(app,), daemon=True)
    thread.start()
    return thread
