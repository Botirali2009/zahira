-- 013_add_motivation_log.sql — dedupe table for motivation messages
-- (Module F). "Not more than once a day" is enforced by checking whether a
-- row already exists for (patient_id, sent_date).
-- Applied migrations are never edited. New change = new numbered file.

CREATE TABLE motivation_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    sent_date  TEXT NOT NULL,   -- "YYYY-MM-DD" local date
    reason     TEXT,            -- 'trend_improved' | 'care_plan_change'
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(patient_id, sent_date)
);
