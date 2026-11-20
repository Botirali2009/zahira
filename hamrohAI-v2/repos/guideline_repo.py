"""SQL for the `guideline_chunks` FTS5 table — the RAG index the "llm"
analyzer (analyzers/{llm,gemini}_analyzer.py) searches before answering, so
its reasoning can point at real guideline text instead of the model's own
memory.
"""

import re

from core import db

# A handful of significant words is enough for bm25 to rank well, and caps
# how large a MATCH query can get from a long patient answer.
_MAX_QUERY_TERMS = 12
_WORD_RE = re.compile(r"[\w']+", re.UNICODE)


def count():
    row = db.query_one("SELECT COUNT(*) AS n FROM guideline_chunks")
    return row["n"] if row else 0


def sources():
    """Distinct source_name values currently indexed."""
    rows = db.query_all(
        "SELECT DISTINCT source_name FROM guideline_chunks ORDER BY source_name")
    return [r["source_name"] for r in rows]


def clear_source(source_name):
    """Remove every chunk for one source — call before re-ingesting it."""
    db.execute(
        "DELETE FROM guideline_chunks WHERE source_name = ?", (source_name,))


def add_chunk(source_name, section_title, content):
    db.execute(
        "INSERT INTO guideline_chunks (source_name, section_title, content) "
        "VALUES (?, ?, ?)",
        (source_name, section_title, content),
    )


_MAX_CHUNK_CHARS = 1200


def _split_long_section(text, max_chars):
    """A section that's grown past a reasonable chunk size gets split on
    paragraph boundaries, not mid-sentence."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        candidate = (current + "\n\n" + para) if current else para
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = para
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or [text]


def ingest_text(source_name, raw_text):
    """Parse `## Heading` — delimited plain text into chunks and (re)index
    them under `source_name`. Safe to call again after editing the source
    file — old chunks for this source are replaced, not accumulated.

    Returns the number of chunks written.
    """
    clear_source(source_name)

    sections = []  # (title, body)
    current_title, current_lines = None, []
    for line in raw_text.splitlines():
        if line.startswith("## "):
            if current_title is not None or current_lines:
                sections.append(
                    (current_title or "Umumiy", "\n".join(current_lines).strip()))
            current_title = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_title is not None or current_lines:
        sections.append(
            (current_title or "Umumiy", "\n".join(current_lines).strip()))

    written = 0
    for title, body in sections:
        if not body:
            continue
        parts = _split_long_section(body, _MAX_CHUNK_CHARS)
        for i, part in enumerate(parts, start=1):
            chunk_title = title if len(parts) == 1 else "{} ({}-qism)".format(title, i)
            add_chunk(source_name, chunk_title, part)
            written += 1
    return written


def _fts_query(text):
    """Turn free-form patient text into a safe FTS5 MATCH expression.

    Uzbek is agglutinative — "terlayapman" (I'm sweating) and "terlaydi"
    (sweats) share a root but not a token, so exact-word matching misses
    almost every real conjugation/declension pair. Longer words become
    prefix queries instead ("terla*") to catch that; short words stay exact
    (a short prefix would match too much to be useful). Every term is still
    either quoted or a plain alphanumeric+prefix token, which neutralises
    FTS5's own query-syntax characters that raw patient text may contain.
    """
    words = _WORD_RE.findall(text or "")
    words = [w for w in words if len(w) > 2][:_MAX_QUERY_TERMS]
    if not words:
        return None
    terms = []
    for w in words:
        w = w.replace('"', "").replace("*", "")
        if not w:
            continue
        stem = w[:5] if len(w) > 4 else w
        terms.append('"{}"*'.format(stem))
    return " OR ".join(terms) if terms else None


def search(query_text, limit=3):
    """Best-matching chunks for free-form text, best first. [] if nothing
    usable — never raises on bad input."""
    fts_query = _fts_query(query_text)
    if not fts_query:
        return []
    try:
        return db.query_all(
            "SELECT source_name, section_title, content "
            "FROM guideline_chunks "
            "WHERE guideline_chunks MATCH ? "
            "ORDER BY bm25(guideline_chunks) LIMIT ?",
            (fts_query, limit),
        )
    except Exception:
        return []
