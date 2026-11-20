"""Turns a patient's free-form answer into the guideline excerpts the "llm"
analyzer (either back end) should read before reasoning about it."""

from repos import guideline_repo

_NO_MATCH_TEXT = (
    "Tegishli qoʻllanma boʻlagi topilmadi — faqat umumiy bilimga tayanib "
    "ehtiyotkorlik bilan xulosa chiqaring va buni reasoning'da ayting."
)


def context_for(query_text, limit=3):
    """Formatted guideline excerpts for `query_text`, or a clear "nothing
    found" instruction — never empty, so the prompt template always has
    something to substitute."""
    chunks = guideline_repo.search(query_text, limit=limit)
    if not chunks:
        return _NO_MATCH_TEXT
    parts = []
    for c in chunks:
        parts.append(
            "[{source} — {section}]\n{content}".format(
                source=c["source_name"],
                section=c["section_title"],
                content=c["content"],
            )
        )
    return "\n\n".join(parts)
