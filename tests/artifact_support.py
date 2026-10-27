"""Self-contained temporary output parents for offline test modules."""
from pathlib import Path


def ensure_artifacts(module):
    path=Path(__file__).resolve().parents[1]/'artifacts/tests'/module
    path.mkdir(parents=True,exist_ok=True)
    return path
