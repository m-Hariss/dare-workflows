import re
from collections import defaultdict, deque

from app.models.workflow import WorkflowGraph, WorkflowNode, WorkflowEdge


def _natural_key(text: str) -> list:
    """Sort key that orders 'Step 2' before 'Step 10' (numeric-aware)."""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", text)]


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
        """Return node IDs sorted so every node comes after its dependencies.

        Entry node always comes first. Any subgraph not reachable from the
        entry node is appended afterwards, still in topological order — so
        nodes with edges between them (e.g. step→output) are ordered
        correctly even when start has no edge to those nodes.
        """
        in_degree = {node_id: 0 for node_id in self.nodes}
        for edge in self.edges:
            if edge.target in in_degree:
                in_degree[edge.target] += 1

        order: list[str] = []
        visited: set[str] = set()

        def _kahn(seeds: list[str]) -> None:
            queue = deque(seeds)
            for s in seeds:
                visited.add(s)
            while queue:
                node_id = queue.popleft()
                order.append(node_id)
                for edge in self.out_edges[node_id]:
                    in_degree[edge.target] -= 1
                    if in_degree[edge.target] == 0 and edge.target not in visited:
                        visited.add(edge.target)
                        queue.append(edge.target)

        # Pass 1: start from the declared entry node
        _kahn([self.entry_node])

        # Pass 2: any remaining disconnected subgraphs, in topological order.
        # Seed with nodes that have no remaining in-edges (roots of those subgraphs).
        # Sort by label so "Step 1" runs before "Step 2" etc. Uses natural sort so
        # "Step 10" doesn't sort before "Step 2".
        remaining_roots = [n for n in self.nodes if n not in visited and in_degree[n] == 0]
        if remaining_roots:
            remaining_roots.sort(key=lambda n: _natural_key(self.nodes[n].data.get("label", "")))
            _kahn(remaining_roots)

        # Pass 3: anything still unvisited (e.g. cycle members) — append as-is
        for node_id in self.nodes:
            if node_id not in visited:
                order.append(node_id)

        return order
