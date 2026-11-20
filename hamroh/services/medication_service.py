"""Medication schedules — written by either side, read by both.

Reminders are driven separately by `services/medication_reminder_scheduler.py`,
which only needs `times_json` + `active` + the date range; nothing here
knows push notifications exist.
"""

import json
import re

from core.errors import NotFound, ValidationError
from repos import medication_repo

TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _as_dict(row):
    return {k: row[k] for k in row.keys()}


def _parse_times(raw_times):
    times = [t.strip() for t in (raw_times or []) if t.strip()]
    if not times:
        raise ValidationError("Kamida bitta ichish vaqti kerak.")
    for t in times:
        if not TIME_RE.match(t):
            raise ValidationError("Vaqt formati noto'g'ri (masalan 08:00).")
    return sorted(set(times))


def _clean(value):
    value = (value or "").strip()
    return value or None


def add(patient_id, actor_role, actor_user_id, drug_name, dose, raw_times,
        start_date, end_date):
    drug_name = _clean(drug_name)
    if not drug_name:
        raise ValidationError("Dori nomi kiritilishi shart.")
    start_date = _clean(start_date)
    if not start_date:
        raise ValidationError("Boshlanish sanasi kiritilishi shart.")

    times = _parse_times(raw_times)
    schedule_id = medication_repo.create(
        patient_id, drug_name, _clean(dose), json.dumps(times),
        start_date, _clean(end_date), actor_role, actor_user_id,
    )
    return _as_dict(medication_repo.get(schedule_id))


def _with_times(row):
    item = _as_dict(row)
    try:
        item["times"] = json.loads(item.pop("times_json") or "[]")
    except (TypeError, ValueError):
        item["times"] = []
    return item


def list_for_patient(patient_id, active_only=False):
    rows = medication_repo.list_for_patient(patient_id, active_only=active_only)
    return [_with_times(r) for r in rows]


def _get_or_404(schedule_id):
    schedule = medication_repo.get(schedule_id)
    if schedule is None:
        raise NotFound("Dori jadvali topilmadi.")
    return schedule


def update(schedule_id, drug_name, dose, raw_times, start_date, end_date):
    _get_or_404(schedule_id)
    drug_name = _clean(drug_name)
    if not drug_name:
        raise ValidationError("Dori nomi kiritilishi shart.")
    start_date = _clean(start_date)
    if not start_date:
        raise ValidationError("Boshlanish sanasi kiritilishi shart.")
    times = _parse_times(raw_times)

    medication_repo.update(
        schedule_id, drug_name, _clean(dose), json.dumps(times), start_date,
        _clean(end_date),
    )
    return _with_times(medication_repo.get(schedule_id))


def stop(schedule_id):
    _get_or_404(schedule_id)
    medication_repo.set_active(schedule_id, False)
    return _with_times(medication_repo.get(schedule_id))


def resume(schedule_id):
    _get_or_404(schedule_id)
    medication_repo.set_active(schedule_id, True)
    return _with_times(medication_repo.get(schedule_id))
