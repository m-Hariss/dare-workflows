# Dare Workflow Runner

FastAPI service that ingests a workflow JSON exported from the Dare platform, parses it into a typed graph, and executes it node by node.

## Phase A — Project Setup

### Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/workflow/upload` | Upload and store a workflow JSON |
| `GET` | `/workflow/info` | Return node count, edge count, topological order |
| `DELETE` | `/workflow/clear` | Remove the stored workflow |
| `GET` | `/health` | Health check |

### Workflow JSON shape

```json
{
  "nodes": [
    { "id": "1", "type": "start", "data": { "label": "Start" }, "position": { "x": 0, "y": 0 } }
  ],
  "edges": [
    { "id": "e1", "source": "1", "target": "2" }
  ]
}
```
