-- 007_add_auth.sql — user accounts + external identity providers (Module A).
-- Applied migrations are never edited. New change = new numbered file.
--
-- `patients`/`doctors` gain a nullable `user_id`: existing demo rows stay
-- NULL and keep working through the old unauthenticated URLs. New rows
-- created through the login flow (modules B/C/D) get a real user_id.

CREATE TABLE users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    role        TEXT,                        -- 'patient' | 'doctor', NULL until chosen
    full_name   TEXT,
    phone       TEXT,
    email       TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE user_identities (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL REFERENCES users(id),
    provider         TEXT NOT NULL,          -- 'google' | 'telegram' | 'dmed'
    external_id      TEXT NOT NULL,          -- the provider's own user id
    raw_profile_json TEXT DEFAULT '{}',
    created_at       TEXT DEFAULT (datetime('now')),
    UNIQUE(provider, external_id)
);

CREATE INDEX idx_user_identities_user ON user_identities(user_id);

ALTER TABLE patients ADD COLUMN user_id INTEGER REFERENCES users(id);
ALTER TABLE doctors  ADD COLUMN user_id INTEGER REFERENCES users(id);

-- One user maps to at most one patient/doctor profile. SQLite treats NULL
-- as distinct in a UNIQUE index, so the many NULL demo rows are unaffected.
CREATE UNIQUE INDEX idx_patients_user ON patients(user_id);
CREATE UNIQUE INDEX idx_doctors_user  ON doctors(user_id);
