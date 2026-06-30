from fastapi import APIRouter, HTTPException, UploadFile, File

from app.storage import file_store

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/{slot_id}")
async def upload_file(slot_id: str, file: UploadFile = File(...)) -> dict:
    """Upload a file into a slot, keeping any existing files."""
    content = await file.read()
    file_store.save(slot_id, file.filename, content)
    return {"slot_id": slot_id, "filename": file.filename}


@router.get("")
def list_files() -> dict:
    """Return all slot -> [filenames] mappings."""
    return file_store.list_slots()


@router.delete("/{slot_id}/{filename}")
def delete_file(slot_id: str, filename: str) -> dict:
    """Remove a specific file from a slot."""
    file_store.delete_file(slot_id, filename)
    return {"message": f"'{filename}' removed from slot '{slot_id}'"}


@router.delete("/{slot_id}")
def delete_slot(slot_id: str) -> dict:
    """Remove all files from a slot."""
    file_store.delete_slot(slot_id)
    return {"message": f"Slot '{slot_id}' cleared"}
