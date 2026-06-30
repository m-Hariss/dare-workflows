from pydantic import ValidationError

from app.models.workflow import WorkflowGraph


def load_workflow(data: dict) -> WorkflowGraph:
    """Validate raw workflow JSON and return a typed WorkflowGraph.

    Raises ValueError with a clear message if the data is invalid.
    """
    try:
        return WorkflowGraph(**data)
    except ValidationError as e:
        raise ValueError(f"Invalid workflow: {e}") from e
