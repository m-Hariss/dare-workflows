from typing import Literal, Optional
from pydantic import BaseModel, model_validator


class WorkflowNode(BaseModel):
    id: str
    type: Literal["start", "step", "file", "router", "output"]
    data: dict


class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None


class WorkflowGraph(BaseModel):
    workflowId: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    mode: Optional[str] = None
    entryNode: str
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]

    @model_validator(mode="after")
    def entry_node_must_exist(self):
        node_ids = {n.id for n in self.nodes}
        if self.entryNode not in node_ids:
            raise ValueError(f"entryNode '{self.entryNode}' not found in nodes")
        return self
