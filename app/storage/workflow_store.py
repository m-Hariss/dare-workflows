import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parents[2] / ".data"
_WORKFLOW_FILE = _DATA_DIR / "workflow.json"


def save(data: dict) -> None:
    """Persist the raw workflow JSON to disk."""
    _DATA_DIR.mkdir(exist_ok=True)
    _WORKFLOW_FILE.write_text(json.dumps(data, indent=2))


def load() -> dict | None:
    """Return the stored workflow JSON, or None if nothing is saved yet."""
    if not _WORKFLOW_FILE.exists():
        return None
    return json.loads(_WORKFLOW_FILE.read_text())


def clear() -> None:
    """Delete the stored workflow from disk."""
    if _WORKFLOW_FILE.exists():
        _WORKFLOW_FILE.unlink()
