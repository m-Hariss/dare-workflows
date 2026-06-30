from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.workflow import router as workflow_router

app = FastAPI(title="Dare Workflow Runner")

app.include_router(workflow_router)

_DASHBOARD = (Path(__file__).resolve().parent / "static" / "dashboard.html").read_text()


@app.get("/", response_class=HTMLResponse)
def root():
    """Serve the dashboard."""
    return HTMLResponse(_DASHBOARD)
