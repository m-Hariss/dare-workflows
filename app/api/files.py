import io
import json
import threading
import traceback
from pathlib import Path

from pypdf import PdfReader

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.storage import file_store
from app.storage.key_store import get as get_key
from app.storage.vector_store import VectorStore
from app.core.chunker import chunk_text
from app.core.embedder import embed_batch

router = APIRouter(prefix="/files", tags=["files"])

_DATA_DIR    = Path(__file__).resolve().parents[2] / ".data"
_STATUS_FILE = _DATA_DIR / "index_status.json"


def _get_vector_store() -> VectorStore:
    return VectorStore.shared(_DATA_DIR)


# ── Index status helpers ──

def _read_status() -> dict:
    if not _STATUS_FILE.exists():
        return {}
    text = _STATUS_FILE.read_text().strip()
    return json.loads(text) if text else {}


def _write_status(key: str, status: dict) -> None:
    """Write status for a single file. Key format: '{slot_id}::{filename}'."""
    _DATA_DIR.mkdir(exist_ok=True)
    all_status = _read_status()
    all_status[key] = status
    _STATUS_FILE.write_text(json.dumps(all_status, indent=2))


def _clear_file_status(slot_id: str, filename: str) -> None:
    """Remove the status entry for one specific file."""
    key = f"{slot_id}::{filename}"
    all_status = _read_status()
    all_status.pop(key, None)
    _STATUS_FILE.write_text(json.dumps(all_status, indent=2))


def _clear_slot_statuses(slot_id: str) -> None:
    """Remove all status entries for every file in a slot."""
    prefix = f"{slot_id}::"
    remaining = {k: v for k, v in _read_status().items() if not k.startswith(prefix)}
    _STATUS_FILE.write_text(json.dumps(remaining, indent=2))


# ── Text extraction ──

def _extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from uploaded file. Handles PDF and plain text."""
    if filename.lower().endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(content))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
    return content.decode("utf-8", errors="replace")


# ── Background indexing ──

def _index_file(slot_id: str, filename: str, content: str) -> None:
    """Chunk, embed and store a file in ChromaDB. Runs in a background thread.

    Solves Problem 1: runs in background so the upload endpoint returns immediately.
    Solves Problem 4: VectorStore uses a lock internally for safe concurrent writes.
    Solves Problem 5: try/except always writes a final status so it never gets stuck.
    """
    key = f"{slot_id}::{filename}"
    try:
        if not get_key("openai"):
            _write_status(key, {"status": "failed", "error": "No OpenAI API key configured. Add one via API Keys."})
            return

        if not content.strip():
            _write_status(key, {"status": "failed", "error": "No text could be extracted from this file."})
            return

        _write_status(key, {"status": "indexing", "chunks": 0})

        # Problem 3: chunk_text keeps chunks small (~1000 chars)
        chunks = chunk_text(content)
        _write_status(key, {"status": "indexing", "chunks": len(chunks)})

        # embed_batch sends in batches of 50 to avoid API limits
        vectors = embed_batch(chunks)

        # delete old vectors for this slot before inserting new ones
        # Problem 2: only re-indexes when a new file is uploaded
        vs = _get_vector_store()
        vs.delete(slot_id)
        vs.upsert(slot_id, chunks, vectors)

        _write_status(key, {"status": "done", "chunks": len(chunks)})

    except Exception as e:
        traceback.print_exc()
        try:
            _write_status(key, {"status": "failed", "error": str(e)})
        except Exception as e2:
            print(f"[index] could not write failed status: {e2}", flush=True)


# ── API endpoints ──

@router.post("/{slot_id}")
async def upload_file(slot_id: str, file: UploadFile = File(...)) -> dict:
    """Upload a file into a slot and start indexing it in the background."""
    content_bytes = await file.read()
    file_store.save(slot_id, file.filename, content_bytes)

    # Write initial status synchronously so the UI can find it as soon as
    # loadSlots() runs — before the background thread has had a chance to start.
    _write_status(f"{slot_id}::{file.filename}", {"status": "indexing", "chunks": 0})

    content_text = _extract_text(file.filename, content_bytes)

    thread = threading.Thread(
        target=_index_file,
        args=(slot_id, file.filename, content_text),
        daemon=True,
    )
    thread.start()

    return {"slot_id": slot_id, "filename": file.filename, "indexing": "started"}


@router.get("/status/{slot_id}")
def get_index_status(slot_id: str) -> dict:
    """Return per-file indexing status for all files in a slot.

    Returns: { filename: { status, chunks, error? }, ... }
    """
    prefix = f"{slot_id}::"
    return {
        key[len(prefix):]: val
        for key, val in _read_status().items()
        if key.startswith(prefix)
    }


@router.get("")
def list_files() -> dict:
    """Return all slot -> [filenames] mappings."""
    return file_store.list_slots()


@router.delete("/{slot_id}/{filename}")
def delete_file(slot_id: str, filename: str) -> dict:
    """Remove a specific file from a slot."""
    file_store.delete_file(slot_id, filename)
    _get_vector_store().delete(slot_id)
    _clear_file_status(slot_id, filename)
    return {"message": f"'{filename}' removed from slot '{slot_id}'"}


@router.get("/debug")
def debug_index() -> dict:
    """Show what's actually stored in ChromaDB — useful for verifying embeddings work."""
    vs = _get_vector_store()
    total_chunks = vs.count()
    status = _read_status()
    return {
        "total_chunks_in_chromadb": total_chunks,
        "slots": {
            slot_id: {
                "status": slot_status.get("status"),
                "file": slot_status.get("file"),
                "chunks_indexed": slot_status.get("chunks", 0),
                "error": slot_status.get("error"),
            }
            for slot_id, slot_status in status.items()
        },
    }


@router.delete("/{slot_id}")
def delete_slot(slot_id: str) -> dict:
    """Remove all files from a slot."""
    file_store.delete_slot(slot_id)
    _get_vector_store().delete(slot_id)
    _clear_slot_statuses(slot_id)
    return {"message": f"Slot '{slot_id}' cleared"}
