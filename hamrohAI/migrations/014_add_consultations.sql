-- 014_add_consultations.sql — one-time doctor consultation requests
-- (Module G). Applied migrations are never edited. New change = new
-- numbered file.

-- Whether this doctor currently wants to receive consultation requests at
-- all, for whichever specialties they're already registered under
-- (doctor_specialties from Module B) — no separate per-specialty toggle.
ALTER TABLE doctors ADD COLUMN consultation_available INTEGER DEFAULT 0;

CREATE TABLE consultations (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id             INTEGER NOT NULL REFERENCES patients(id),
    specialty_id           INTEGER NOT NULL REFERENCES specialties(id),
    question               TEXT NOT NULL,
    snapshot_json          TEXT NOT NULL,   -- diagnoses + active meds + profile, frozen at request time
    status                 TEXT DEFAULT 'open',  -- 'open'|'accepted'|'answered'|'cancelled'
    accepted_by_doctor_id  INTEGER REFERENCES doctors(id),
    accepted_at            TEXT,
    answer_text            TEXT,
    answered_at            TEXT,
    created_at             TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_consultations_patient            ON consultations(patient_id);
CREATE INDEX idx_consultations_specialty_status    ON consultations(specialty_id, status);
CREATE INDEX idx_consultations_accepted_by         ON consultations(accepted_by_doctor_id);
