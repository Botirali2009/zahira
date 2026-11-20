-- 010_add_medications_diagnoses.sql — shared medication + diagnosis data
-- (Module E). Both the doctor and the patient can write to these; who wrote
-- what is recorded for audit but never restricts who may edit next.
-- Applied migrations are never edited. New change = new numbered file.

CREATE TABLE diagnoses (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id         INTEGER NOT NULL REFERENCES patients(id),
    text               TEXT NOT NULL,
    status             TEXT DEFAULT 'active',   -- 'active' | 'closed'
    created_by         TEXT NOT NULL,           -- 'doctor' | 'patient'
    created_by_user_id INTEGER REFERENCES users(id),
    created_at         TEXT DEFAULT (datetime('now')),
    updated_at         TEXT DEFAULT (datetime('now'))
);

CREATE TABLE diagnosis_files (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    diagnosis_id      INTEGER NOT NULL REFERENCES diagnoses(id),
    file_path         TEXT NOT NULL,           -- relative to Config.UPLOAD_DIR
    original_filename TEXT,
    content_type      TEXT,
    analyzed          INTEGER DEFAULT 0,       -- future AI-analysis extension point
    uploaded_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE medication_schedules (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id         INTEGER NOT NULL REFERENCES patients(id),
    drug_name          TEXT NOT NULL,
    dose               TEXT,
    times_json         TEXT DEFAULT '[]',      -- JSON array of "HH:MM" local times
    start_date         TEXT,
    end_date           TEXT,                   -- NULL = ongoing
    active             INTEGER DEFAULT 1,
    created_by         TEXT NOT NULL,           -- 'doctor' | 'patient'
    created_by_user_id INTEGER REFERENCES users(id),
    created_at         TEXT DEFAULT (datetime('now')),
    updated_at         TEXT DEFAULT (datetime('now'))
);

-- Dedupe table for the reminder scheduler: one row per (schedule, time-slot,
-- calendar day) it has already pushed, so a scheduler tick never double-fires.
CREATE TABLE medication_reminders_sent (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    medication_schedule_id  INTEGER NOT NULL REFERENCES medication_schedules(id),
    reminder_time           TEXT NOT NULL,      -- "HH:MM" slot that fired
    sent_date               TEXT NOT NULL,      -- "YYYY-MM-DD" local date
    sent_at                 TEXT DEFAULT (datetime('now')),
    UNIQUE(medication_schedule_id, reminder_time, sent_date)
);

CREATE INDEX idx_diagnoses_patient          ON diagnoses(patient_id);
CREATE INDEX idx_diagnosis_files_diagnosis  ON diagnosis_files(diagnosis_id);
CREATE INDEX idx_medication_schedules_pat   ON medication_schedules(patient_id, active);
