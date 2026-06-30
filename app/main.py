from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.workflow import router as workflow_router
from app.api.keys import router as keys_router

app = FastAPI(title="Dare Workflow Runner")

app.include_router(workflow_router)
app.include_router(keys_router)

_DASHBOARD = (Path(__file__).resolve().parent / "static" / "dashboard.html").read_text()


@app.get("/", response_class=HTMLResponse)
def root():
    """Serve the dashboard."""
    return HTMLResponse(_DASHBOARD)
