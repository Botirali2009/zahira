"""Congratulating a patient on real progress (Module F).

Deliberately separate from the risk-analysis pipeline in `analyzers/` even
though it reacts to the same `assessment.created` event — this has nothing
to do with detecting danger, so it doesn't live there, doesn't run in that
pipeline, and can't affect a risk verdict. It reuses the same `ai_assessments`
history the existing (doctor-only) trend chart already reads — Module F's
own framing is "the patient can't see what the doctor already can," not "a
new data source."
"""

from datetime import datetime, timedelta

from analyzers.base import RISK_ORDER
from config import features
from notifiers import push_notifier
from repos import assessment_repo, diagnosis_repo, medication_repo, motivation_log_repo

IMPROVEMENT_SCORE_DELTA = 15
CARE_PLAN_WINDOW_DAYS = 7

MESSAGES = {
    "care_plan_change": (
        "Ajoyib xabar! Shifokoringiz dori/tashxisni yangilagandan beri "
        "ko'rsatkichlaringiz yaxshilanmoqda. Shunday davom eting!"
    ),
    "trend_improved": (
        "Zo'r natija! So'nggi kunlarda ko'rsatkichlaringiz sezilarli "
        "yaxshilanmoqda. Shunday davom eting!"
    ),
}


def _has_genuine_improvement(points):
    if len(points) < 2:
        return False
    prev, curr = points[-2], points[-1]
    prev_rank = RISK_ORDER.get(prev["risk_level"], 0)
    curr_rank = RISK_ORDER.get(curr["risk_level"], 0)
    if curr_rank < prev_rank:
        return True
    return (curr_rank == prev_rank
            and (prev["risk_score"] - curr["risk_score"]) >= IMPROVEMENT_SCORE_DELTA)


def _care_plan_recently_changed(patient_id, now):
    threshold = (now - timedelta(days=CARE_PLAN_WINDOW_DAYS)).strftime("%Y-%m-%d %H:%M:%S")
    for row in medication_repo.list_for_patient(patient_id):
        if row["updated_at"] and row["updated_at"] >= threshold:
            return True
    for row in diagnosis_repo.list_for_patient(patient_id):
        if row["updated_at"] and row["updated_at"] >= threshold:
            return True
    return False


def evaluate_and_notify(patient_id, now=None):
    """Returns True if a motivation message was sent. Called from
    hooks/motivation_hooks.py on every new assessment; tests call it
    directly to avoid depending on the full check-in pipeline."""
    if not features.enabled("motivation_messages"):
        return False

    now = now or datetime.now()
    today = now.strftime("%Y-%m-%d")
    if motivation_log_repo.was_sent_today(patient_id, today):
        return False

    points = [dict(r) for r in assessment_repo.trend_for_patient(patient_id)]
    if not _has_genuine_improvement(points):
        return False

    reason = "care_plan_change" if _care_plan_recently_changed(patient_id, now) else "trend_improved"
    motivation_log_repo.mark_sent(patient_id, today, reason)
    push_notifier.send_to_subscriber(
        "patient", patient_id,
        title="Yaxshi xabar!",
        body=MESSAGES[reason],
        url="/patient/%d/chat" % patient_id,
    )
    return True
