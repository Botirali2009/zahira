-- 012_patients_doctor_id_nullable.sql — self-signup patients (Module D)
-- start with no doctor at all. SQLite can't drop a NOT NULL constraint
-- with a plain ALTER, so this rebuilds the table the standard SQLite way:
-- copy into a new table with the relaxed schema, drop the old one, rename.
-- Every row's `id` is preserved explicitly, so every foreign key in
-- checkins/messages/ai_assessments/alerts/call_log/diagnoses/
-- medication_schedules/invite_codes that points at patients(id) stays valid.
-- Applied migrations are never edited. New change = new numbered file.

CREATE TABLE patients_new (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name      TEXT NOT NULL,
    persona_key    TEXT NOT NULL,
    diagnosis      TEXT,
    discharge_date TEXT,
    phone_sim      TEXT,
    doctor_id      INTEGER REFERENCES doctors(id),   -- now nullable
    current_day    INTEGER DEFAULT 0,
    risk_level     TEXT    DEFAULT 'green',
    meta_json      TEXT    DEFAULT '{}',
    user_id        INTEGER REFERENCES users(id),
    created_at     TEXT    DEFAULT (datetime('now'))
);

INSERT INTO patients_new
    (id, full_name, persona_key, diagnosis, discharge_date, phone_sim,
     doctor_id, current_day, risk_level, meta_json, user_id, created_at)
SELECT id, full_name, persona_key, diagnosis, discharge_date, phone_sim,
       doctor_id, current_day, risk_level, meta_json, user_id, created_at
  FROM patients;

DROP TABLE patients;
ALTER TABLE patients_new RENAME TO patients;

-- Indexes live on the table, not carried over by rename — recreate them.
CREATE UNIQUE INDEX idx_patients_user ON patients(user_id);

-- Doctor's reusable, expiring connect code (Module D) — distinct from
-- Module C's one-time invite_codes. Multiple patients may use the same
-- code; the doctor can regenerate it (e.g. for security).
ALTER TABLE doctors ADD COLUMN connect_code TEXT;
ALTER TABLE doctors ADD COLUMN connect_code_expires_at TEXT;

CREATE UNIQUE INDEX idx_doctors_connect_code ON doctors(connect_code);
