-- 011_add_invite_codes.sql — doctor-issued, one-time, pre-linked invite
-- codes (Module C). Not time-limited — Module D's separate doctor connect
-- code is the multi-use, expiring one.
-- Applied migrations are never edited. New change = new numbered file.

CREATE TABLE invite_codes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,
    patient_id      INTEGER NOT NULL REFERENCES patients(id),
    doctor_id       INTEGER NOT NULL REFERENCES doctors(id),
    used            INTEGER DEFAULT 0,
    used_by_user_id INTEGER REFERENCES users(id),
    used_at         TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_invite_codes_doctor ON invite_codes(doctor_id);
