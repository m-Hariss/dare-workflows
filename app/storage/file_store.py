import io
import json
import shutil
from pathlib import Path

from pypdf import PdfReader

_DATA_DIR    = Path(__file__).resolve().parents[2] / ".data"
_UPLOADS_DIR = _DATA_DIR / "uploads"
_MAP_FILE    = _DATA_DIR / "file_map.json"


def _read_map() -> dict:
    """Read the slot -> [filenames] mapping from disk."""
    if not _MAP_FILE.exists():
        return {}
    return json.loads(_MAP_FILE.read_text())


def _write_map(data: dict) -> None:
    """Write the slot -> [filenames] mapping to disk."""
    _DATA_DIR.mkdir(exist_ok=True)
    _MAP_FILE.write_text(json.dumps(data, indent=2))


def save(slot_id: str, filename: str, content: bytes) -> None:
    """Save an uploaded file into its slot folder, keeping existing files."""
    slot_dir = _UPLOADS_DIR / slot_id
    slot_dir.mkdir(parents=True, exist_ok=True)

    (slot_dir / filename).write_bytes(content)

    file_map = _read_map()
    files = file_map.get(slot_id, [])
    if filename not in files:
        files.append(filename)
    file_map[slot_id] = files
    _write_map(file_map)


def get_content(slot_id: str) -> str:
    """Read and return the combined text content of all files in a slot.

    Returns an empty string if no files have been uploaded — callers that need
    files should handle the empty-string case rather than depending on an
    exception for control flow.
    """
    file_map = _read_map()
    filenames = file_map.get(slot_id, [])
    if not filenames:
        return ""

    contents = []
    for filename in filenames:
        file_path = _UPLOADS_DIR / slot_id / filename
        if not file_path.exists():
            continue
        text = _read_file_text(file_path, filename)
        if text.strip():
            contents.append(f"--- {filename} ---\n{text}")

    return "\n\n".join(contents)


def _read_file_text(file_path: Path, filename: str) -> str:
    """Extract plain text from a file. Handles PDF and plain-text formats."""
    if filename.lower().endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(file_path.read_bytes()))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
    return file_path.read_text(errors="replace")


def list_slots() -> dict:
    """Return all slot -> [filenames] mappings."""
    return _read_map()


def delete_file(slot_id: str, filename: str) -> None:
    """Remove a specific file from a slot."""
    file_map = _read_map()
    files = file_map.get(slot_id, [])

    if filename in files:
        files.remove(filename)
        file_path = _UPLOADS_DIR / slot_id / filename
        if file_path.exists():
            file_path.unlink()

    if files:
        file_map[slot_id] = files
    else:
        file_map.pop(slot_id, None)

    _write_map(file_map)


def delete_slot(slot_id: str) -> None:
    """Remove all files from a slot."""
    file_map = _read_map()
    filenames = file_map.pop(slot_id, [])

    for filename in filenames:
        file_path = _UPLOADS_DIR / slot_id / filename
        if file_path.exists():
            file_path.unlink()

    _write_map(file_map)


def clear_all() -> None:
    """Remove every uploaded file and reset the file map."""
    if _UPLOADS_DIR.exists():
        shutil.rmtree(_UPLOADS_DIR)
    _write_map({})
