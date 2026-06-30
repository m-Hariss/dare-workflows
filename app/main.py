from fastapi import FastAPI

from app.api.workflow import router as workflow_router

app = FastAPI(title="Dare Workflow Runner")

app.include_router(workflow_router)
