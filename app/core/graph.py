from collections import defaultdict, deque

from app.models.workflow import WorkflowGraph, WorkflowNode, WorkflowEdge


class Graph:
    def __init__(self, workflow: WorkflowGraph):
        self.entry_node: str = workflow.entryNode
        self.nodes: dict[str, WorkflowNode] = {n.id: n for n in workflow.nodes}
        self.edges: list[WorkflowEdge] = workflow.edges

        self.out_edges: dict[str, list[WorkflowEdge]] = defaultdict(list)
        self.in_edges: dict[str, list[WorkflowEdge]] = defaultdict(list)

        for edge in self.edges:
            self.out_edges[edge.source].append(edge)
            self.in_edges[edge.target].append(edge)

    def topological_order(self) -> list[str]:
        """Return node IDs sorted so every node comes after its dependencies."""
        in_degree = {node_id: 0 for node_id in self.nodes}

        for edge in self.edges:
            if edge.target in in_degree:
                in_degree[edge.target] += 1

        queue = deque([self.entry_node])
        visited = {self.entry_node}
        order = []

        while queue:
            node_id = queue.popleft()
            order.append(node_id)

            for edge in self.out_edges[node_id]:
                in_degree[edge.target] -= 1
                if in_degree[edge.target] == 0 and edge.target not in visited:
                    visited.add(edge.target)
                    queue.append(edge.target)

        # Add any remaining nodes not reachable via edges (disconnected nodes)
        for node_id in self.nodes:
            if node_id not in visited:
                order.append(node_id)

        return order
