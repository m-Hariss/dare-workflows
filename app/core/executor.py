import traceback
from pathlib import Path

from app.core.graph import Graph
from app.core.llm import call_llm
from app.core.embedder import embed_one
from app.storage.vector_store import VectorStore
from app.storage import file_store
from app.storage import run_store


def execute_workflow(run_id: str, workflow, data_dir: Path) -> None:
    """Run every node in topological order and save outputs as they complete.

    All nodes run in order by default. Router nodes prune their unchosen
    branches — any node whose EVERY predecessor was pruned is also skipped.

    Context flow:
      Each node's input = concatenated outputs of its predecessors that ran.
      Step nodes may also pull in raw file content or RAG chunks on top.
    """
    vs = VectorStore.shared(data_dir)
    graph = Graph(workflow)
    order = graph.topological_order()

    outputs: dict[str, str] = {}        # node_id → text the node produced
    skipped: set[str] = set()           # nodes pruned by a router's unchosen branch
    step_history: list[tuple[str, str]] = []  # (label, output) for every completed step

    print(f"[executor] {run_id} order={order}", flush=True)

    try:
        for node_id in order:
            # Skip if explicitly pruned, OR if every predecessor was pruned
            # (meaning this node is unreachable on the active branch).
            # in_edges stores WorkflowEdge objects — compare source IDs.
            preds = graph.in_edges.get(node_id, [])
            pred_ids_check = [e.source for e in preds]
            if node_id in skipped or (pred_ids_check and all(p in skipped for p in pred_ids_check)):
                skipped.add(node_id)
                print(f"[executor] {run_id} SKIP {node_id}", flush=True)
                continue

            node = graph.nodes[node_id]
            label = node.data.get("label", node.type)
            print(f"[executor] {run_id} RUN  {node.type}:{node_id[:8]} label={label!r}", flush=True)

            # Build input from directly connected predecessors.
            pred_ids = [e.source for e in preds]
            input_text = "\n\n".join(outputs[p] for p in pred_ids if p in outputs)

            if node.type == "start":
                outputs[node_id] = ""

            elif node.type == "step":
                use_prev = node.data.get("usePreviousContext", True)
                # When a step has no direct predecessor edges but usePreviousContext is
                # true, fall back to the accumulated outputs of all prior steps.
                # This is the common pattern for sequential workflows where the designer
                # omits inter-step edges and relies on execution order for context.
                if use_prev and not input_text and step_history:
                    input_text = "\n\n".join(f"[{lbl}]:\n{out}" for lbl, out in step_history)

                instruction = node.data.get("textInput", "")
                output = _run_step(node, input_text, vs)
                outputs[node_id] = output
                step_history.append((label, output))
                print(f"[executor] {run_id} step output len={len(output)}", flush=True)
                run_store.add_node_output(run_id, node_id, label, output, instruction)

            elif node.type == "file":
                content = file_store.get_content(node.id)
                outputs[node_id] = content or ""

            elif node.type == "router":
                chosen = _run_router(node, input_text, workflow)
                outputs[node_id] = chosen
                run_store.add_node_output(run_id, node_id, label, f"Routed → {chosen}")
                # Prune every branch whose edge handle doesn't match the choice
                for edge in workflow.edges:
                    if edge.source == node_id:
                        if (edge.sourceHandle or "").strip().lower() != chosen.strip().lower():
                            skipped.add(edge.target)

            elif node.type == "output":
                # Store result for final_output assembly — don't add to node_outputs
                # since the step that feeds this node already has its own section.
                outputs[node_id] = input_text

        # Collect every output-node result in execution order.
        output_results = [
            (graph.nodes[n].data.get("label", "Output"), outputs[n])
            for n in order
            if n in outputs and graph.nodes[n].type == "output" and outputs.get(n)
        ]

        if len(output_results) == 1:
            final = output_results[0][1]
        elif len(output_results) > 1:
            # Multiple output nodes (parallel chains) — label each section.
            final = "\n\n".join(f"### {lbl}\n{text}" for lbl, text in output_results)
        else:
            # No output node — use the last non-empty step output.
            final = next((outputs[n] for n in reversed(order) if outputs.get(n)), "")

        run_store.update(run_id, {"status": "done", "final_output": final})
        print(f"[executor] {run_id} DONE output_nodes={len(output_results)} final len={len(final)}", flush=True)

    except Exception as e:
        traceback.print_exc()
        run_store.update(run_id, {"status": "failed", "error": str(e)})


# ── Node handlers ─────────────────────────────────────────────────────────────

def _run_step(node, input_text: str, vs: VectorStore) -> str:
    """Build the full prompt for a step node and call its LLM."""
    data = node.data

    # prompt can be a plain string or {"title": "...", "content": "..."}
    raw_prompt = data.get("prompt", "")
    prompt = raw_prompt.get("content", "") if isinstance(raw_prompt, dict) else (raw_prompt or "")

    # Extra instructions the user typed when building the workflow
    text_input = data.get("textInput", "")

    # llm is {"provider": "openai", "identifier": "gpt-4.1", "name": "GPT-4.1", ...}
    llm_cfg  = data.get("llm") or {}
    provider = llm_cfg.get("provider", "openai") if isinstance(llm_cfg, dict) else "openai"
    model    = (llm_cfg.get("identifier") or llm_cfg.get("name", "")) if isinstance(llm_cfg, dict) else ""

    gen      = data.get("generation") or {}
    max_tok  = gen.get("maxTokens", 2048)   if isinstance(gen, dict) else 2048
    temp     = gen.get("temperature", 0.7)  if isinstance(gen, dict) else 0.7

    retrieval   = data.get("retrieval") or {}
    top_k       = retrieval.get("maxContextSnippets", 4)   if isinstance(retrieval, dict) else 4
    threshold   = retrieval.get("similarityThreshold", 0.2) if isinstance(retrieval, dict) else 0.2

    system = data.get("systemPrompt", "")
    use_prev = data.get("usePreviousContext", True)

    context_parts = []

    # 1. Previous step's output (if the node is configured to use it)
    if use_prev and input_text:
        context_parts.append(input_text)

    # 2. Raw file content injection
    if data.get("needsContentFiles"):
        content = file_store.get_content(node.id)
        if content:
            context_parts.append(f"--- File Content ---\n{content}")

    # 3. RAG: embed the query and retrieve the most relevant chunks
    if data.get("needsEmbeddingFiles"):
        query = f"{prompt}\n{text_input}\n{input_text}".strip()
        if query:
            query_vector = embed_one(query)
            chunks = vs.query(query_vector, top_k=top_k, threshold=threshold, slot_ids=[node.id])
            if chunks:
                relevant = "\n\n".join(c["text"] for c in chunks)
                context_parts.append(f"--- Relevant Excerpts ---\n{relevant}")

    # Build the final user message: context first, then the actual instructions
    instructions = "\n\n".join(filter(None, [prompt, text_input]))
    full_prompt  = "\n\n".join(context_parts + [instructions]) if context_parts else instructions

    return call_llm(provider, model, system, full_prompt, temperature=temp, max_tokens=max_tok)


def _run_router(node, input_text: str, workflow) -> str:
    """Ask the LLM to pick one of the router's outgoing branches."""
    data = node.data

    raw_prompt = data.get("prompt", "")
    prompt = raw_prompt.get("content", "") if isinstance(raw_prompt, dict) else (raw_prompt or "")

    llm_cfg  = data.get("llm") or {}
    provider = llm_cfg.get("provider", "openai") if isinstance(llm_cfg, dict) else "openai"
    model    = (llm_cfg.get("identifier") or llm_cfg.get("name", "")) if isinstance(llm_cfg, dict) else ""

    options = [
        e.sourceHandle for e in workflow.edges
        if e.source == node.id and e.sourceHandle
    ]

    system = (
        "You are a routing assistant. "
        "Respond with ONLY the exact option label from the list — "
        "no explanation, no punctuation, just the label."
    )
    user = f"{prompt}\n\nOptions: {', '.join(options)}\n\nInput:\n{input_text}"

    response = call_llm(provider, model, system, user).strip()

    for option in options:
        if option.strip().lower() == response.lower():
            return option

    return options[0] if options else response
