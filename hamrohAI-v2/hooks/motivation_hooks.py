"""React to a new assessment by checking whether it's worth celebrating.

Subscribes to `assessment.created` — the exact same event the risk-alert
pipeline reacts to (see `hooks/analysis_hooks.py`/`hooks/alert_hooks.py`),
but this file never touches risk logic itself, only
`services/motivation_service.py`. Deleting this file turns motivation
messages off without affecting risk analysis or alerting at all.
"""

from core import events
from services import motivation_service


@events.on(events.ASSESSMENT_CREATED)
def maybe_send_motivation(patient_id, **_ignored):
    motivation_service.evaluate_and_notify(patient_id)
