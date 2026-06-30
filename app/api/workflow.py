from fastapi import APIRouter, HTTPException

from app.core.loader import load_workflow
from app.core.graph import Graph
from app.storage import workflow_store

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
    """Delete the stored workflow from disk."""
    workflow_store.clear()
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
                slots.append({
                    "slot_id": node.id,
                    "label":   node.data.get("label", "Untitled Step"),
                    "needs_content":   needs_content,
                    "needs_embedding": needs_embedding,
                })

    return {"slots": slots}
