"""Push a reminder when a medication dose comes due.

Subscribes to `medication.reminder_due`, emitted by
`services/medication_reminder_scheduler.py`. Reuses the existing Web Push
channel from Module A/the push-notifications feature — no new notification
channel needed, per the module's own requirement. Deleting this file makes
reminders silent (still detected and logged in `event_log`) without
touching the scheduler.
"""

from core import events
from notifiers import push_notifier

REMINDER_TITLE = "Dori vaqti keldi"


@events.on(events.MEDICATION_REMINDER_DUE)
def push_medication_reminder(patient_id, drug_name, time, **_ignored):
    push_notifier.send_to_subscriber(
        "patient", patient_id,
        title=REMINDER_TITLE,
        body="%s — soat %s da qabul qilish vaqti keldi." % (drug_name, time),
        url="/patient/%d/chat" % patient_id,
    )
