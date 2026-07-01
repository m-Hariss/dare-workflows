from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.core.loader import load_workflow
from app.core.graph import Graph
from app.storage import workflow_store
from app.storage import file_store
from app.storage.vector_store import VectorStore

_DATA_DIR    = Path(__file__).resolve().parents[2] / ".data"
_STATUS_FILE = _DATA_DIR / "index_status.json"

router = APIRouter(prefix="/workflow", tags=["workflow"])


@router.post("/upload")
def upload_workflow(data: dict) -> dict:
    """Accept a workflow JSON, validate it, and save it to disk."""
    try:
        workflow = load_workflow(data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    workflow_store.save(data)
    graph = Graph(workflow)

    return {
        "title": workflow.title,
        "node_count": len(workflow.nodes),
        "entry_node": workflow.entryNode,
        "order": graph.topological_order(),
    }


@router.get("/info")
def get_workflow_info() -> dict:
    """Return metadata about the currently stored workflow."""
    data = workflow_store.load()
    if data is None:
        raise HTTPException(status_code=404, detail="No workflow uploaded yet")

    workflow = load_workflow(data)
    return {
        "title": workflow.title,
        "description": workflow.description,
        "mode": workflow.mode,
        "node_count": len(workflow.nodes),
        "nodes": [{"id": n.id, "type": n.type, "label": n.data.get("label")} for n in workflow.nodes],
    }


@router.delete("/clear")
def clear_workflow() -> dict:
    """Delete the stored workflow and all associated files, embeddings and index status."""
    workflow_store.clear()
    file_store.clear_all()
    VectorStore.shared(_DATA_DIR).delete_all()
    if _STATUS_FILE.exists():
        _STATUS_FILE.write_text("{}")
    return {"message": "Workflow cleared"}


@router.get("/slots")
def get_slots() -> dict:
    """Return the file slots required by the current workflow."""
    data = workflow_store.load()
    if data is None:
        raise HTTPException(status_code=404, detail="No workflow uploaded yet")

    workflow = load_workflow(data)
    slots = []

    for node in workflow.nodes:
        if node.type == "step":
            needs_content   = node.data.get("needsContentFiles", False)
            needs_embedding = node.data.get("needsEmbeddingFiles", False)
            if needs_content or needs_embedding:
                raw_prompt = node.data.get("prompt", "")
                if isinstance(raw_prompt, dict):
                    prompt_text = raw_prompt.get("content") or raw_prompt.get("text") or ""
                else:
                    prompt_text = raw_prompt or ""

                slots.append({
                    "slot_id":         node.id,
                    "label":           node.data.get("label", "Untitled Step"),
                    "prompt":          prompt_text,
                    "needs_content":   needs_content,
                    "needs_embedding": needs_embedding,
                })

    return {"slots": slots}
