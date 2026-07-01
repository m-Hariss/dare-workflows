import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.core.loader import load_workflow
from app.core.executor import execute_workflow
from app.storage import workflow_store
from app.storage import run_store

router = APIRouter(prefix="/run", tags=["run"])

_DATA_DIR = Path(__file__).resolve().parents[2] / ".data"

_counter = 0
_counter_lock = threading.Lock()


def _new_run_id() -> str:
    global _counter
    with _counter_lock:
        _counter += 1
        return f"run_{_counter:04d}"


@router.post("")
def start_run() -> dict:
    """Start executing the stored workflow in a background thread.

    Returns a run_id immediately. Poll GET /run/{run_id} for status and output.
    """
    data = workflow_store.load()
    if data is None:
        raise HTTPException(status_code=404, detail="No workflow uploaded yet.")

    workflow = load_workflow(data)
    run_id = _new_run_id()

    # Write the initial record so the poll endpoint doesn't 404 right away
    run_store.save(run_id, {
        "run_id":       run_id,
        "status":       "running",
        "node_outputs": {},
        "final_output": None,
        "error":        None,
    })

    thread = threading.Thread(
        target=execute_workflow,
        args=(run_id, workflow, _DATA_DIR),
        daemon=True,
    )
    thread.start()

    return {"run_id": run_id, "status": "running"}


@router.get("/{run_id}")
def get_run(run_id: str) -> dict:
    """Return the current state of a workflow run."""
    result = run_store.get(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    return result
