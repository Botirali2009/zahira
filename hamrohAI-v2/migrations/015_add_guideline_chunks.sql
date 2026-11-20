-- Full-text index of official guideline excerpts, used by the "llm" analyzer
-- (both back ends — see analyzers/{llm,gemini}_analyzer.py) to ground its
-- reasoning in real source text instead of the model's own memory.
--
-- FTS5 is used directly as storage (not "external content" mode) — the
-- corpus here is a handful of documents, a few hundred chunks at most, so
-- the usual external-content-table-plus-triggers setup would be pure
-- overhead. UNINDEXED columns hold metadata that should never itself be a
-- text-search match target.
CREATE VIRTUAL TABLE guideline_chunks USING fts5(
    source_name UNINDEXED,   -- e.g. "Milliy klinik protokol 180-son"
    section_title UNINDEXED, -- heading this chunk came from
    content,                 -- the searchable text itself
    tokenize = 'unicode61'
);
