-- 008_add_doctor_profile.sql — doctor profile completion + verification (Module B).
-- Applied migrations are never edited. New change = new numbered file.

ALTER TABLE doctors ADD COLUMN birth_date TEXT;
ALTER TABLE doctors ADD COLUMN experience_years INTEGER;
ALTER TABLE doctors ADD COLUMN workplace TEXT;
ALTER TABLE doctors ADD COLUMN verified INTEGER DEFAULT 0;
ALTER TABLE doctors ADD COLUMN profile_completed INTEGER DEFAULT 0;

-- Legacy/demo doctors (no user_id, predate the auth system) are not part of
-- the new approval workflow — treat them as already verified so nothing
-- about the existing demo looks "unverified".
UPDATE doctors SET verified = 1, profile_completed = 1 WHERE user_id IS NULL;

CREATE TABLE specialties (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    key   TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL
);

CREATE TABLE doctor_specialties (
    doctor_id    INTEGER NOT NULL REFERENCES doctors(id),
    specialty_id INTEGER NOT NULL REFERENCES specialties(id),
    PRIMARY KEY (doctor_id, specialty_id)
);

CREATE TABLE doctor_documents (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_id         INTEGER NOT NULL REFERENCES doctors(id),
    doc_type          TEXT DEFAULT 'diploma',  -- 'diploma' | 'license'
    file_path         TEXT NOT NULL,           -- relative to Config.UPLOAD_DIR
    original_filename TEXT,
    content_type      TEXT,
    uploaded_at       TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_doctor_documents_doctor ON doctor_documents(doctor_id);

-- Admin is an operational flag, not a third role alongside patient/doctor —
-- see services/auth_service.sync_admin_flag() (email-allowlist bootstrap).
ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0;
