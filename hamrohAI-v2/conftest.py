"""Ensures the project root is on sys.path so `import app`, `from config import Config`,
etc. resolve when running plain `pytest` from the project root — no PYTHONPATH needed."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
