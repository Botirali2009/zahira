"""Notify doctors of a new consultation request, and the patient of its
answer. Subscribes to `consultation.requested`/`consultation.answered` —
`services/consultation_service.py` never imports `notifiers` itself, it
just announces what happened. Deleting this file makes consultations
silent (still fully functional; a doctor would just have to check the
list page instead of getting pushed) without touching the state machine.
"""

from core import events
from repos import consultation_repo, doctor_repo
from notifiers import push_notifier

REQUEST_TITLE = "Yangi konsultatsiya so'rovi"
ANSWER_TITLE = "Shifokor javob berdi"


@events.on(events.CONSULTATION_REQUESTED)
def notify_matching_doctors(consultation_id, specialty_id, **_ignored):
    consultation = consultation_repo.get(consultation_id)
    if consultation is None:
        return
    for doctor in doctor_repo.list_available_for_specialty(specialty_id):
        push_notifier.send_to_subscriber(
            "doctor", doctor["id"],
            title=REQUEST_TITLE,
            body=consultation["question"][:140],
            url="/doctor/consultations",
        )


@events.on(events.CONSULTATION_ANSWERED)
def notify_patient(consultation_id, patient_id, **_ignored):
    push_notifier.send_to_subscriber(
        "patient", patient_id,
        title=ANSWER_TITLE,
        body="Sizning savolingizga javob keldi.",
        url="/patient/consultations",
    )
