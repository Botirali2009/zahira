"""Manually (re)ingest one guideline text file into guideline_chunks.

Usage:
    python scripts/ingest_guidelines.py data/guidelines/qollanma_1.txt ["Manba nomi"]

Automatic ingestion already happens on every app start for any file in
data/guidelines/ that isn't indexed yet (see app.py:_auto_ingest_guidelines).
Use this script when you've *edited* an already-ingested file and want the
index updated immediately, without restarting the app.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app  # noqa: E402
from repos import guideline_repo  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)

    path = sys.argv[1]
    source_name = (
        sys.argv[2] if len(sys.argv) > 2
        else os.path.splitext(os.path.basename(path))[0]
    )

    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()

    app = create_app()
    with app.app_context():
        n = guideline_repo.ingest_text(source_name, text)
    print("Ingested {} chunks under source_name={!r}".format(n, source_name))


if __name__ == "__main__":
    main()
