import json
from pathlib import Path

_RUNS_DIR = Path(__file__).resolve().parents[2] / ".data" / "runs"


def save(run_id: str, data: dict) -> None:
    """Write the full run record to disk."""
    _RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (_RUNS_DIR / f"{run_id}.json").write_text(json.dumps(data, indent=2))


def get(run_id: str) -> dict | None:
    """Read a run record. Returns None if it doesn't exist."""
    path = _RUNS_DIR / f"{run_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def update(run_id: str, fields: dict) -> None:
    """Merge fields into an existing run record."""
    current = get(run_id) or {}
    current.update(fields)
    save(run_id, current)


def add_node_output(run_id: str, node_id: str, label: str, output: str, instruction: str = "") -> None:
    """Append a single node's output to the run record."""
    current = get(run_id) or {}
    node_outputs = current.get("node_outputs", {})
    node_outputs[node_id] = {"label": label, "output": output, "instruction": instruction}
    current["node_outputs"] = node_outputs
    save(run_id, current)
