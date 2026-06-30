from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.storage import key_store

router = APIRouter(prefix="/keys", tags=["keys"])


class KeyPayload(BaseModel):
    provider: str
    value: str


@router.post("")
def save_key(payload: KeyPayload) -> dict:
    """Save an API key or Ollama host URL for a provider."""
    try:
        key_store.set(payload.provider, payload.value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"{payload.provider} key saved"}


@router.get("/status")
def get_status() -> dict:
    """Return which providers have a key configured."""
    return key_store.all_statuses()


@router.delete("/{provider}")
def delete_key(provider: str) -> dict:
    """Remove the API key for a provider."""
    key_store.delete(provider)
    return {"message": f"{provider} key removed"}
