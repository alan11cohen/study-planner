# US3 — Planning Agent: Technical Decisions

## What it does

`POST /plans/{id}/agent-generate-tasks` runs a multi-step LangGraph agent that:
1. Retrieves relevant context from uploaded documents (if any).
2. Decomposes the plan's goal into concrete subtopics.
3. Generates study tasks covering those subtopics (reusing the `TaskGenerator` from US1).
4. Validates that the tasks fit within the plan's remaining hours budget (total budget minus hours already allocated to existing tasks).
5. If constraints are violated, asks the LLM to adjust the task list and re-validates (up to `AGENT_MAX_ATTEMPTS` times).
6. If all attempts fail, persists a valid subset (salvage) rather than returning an error.

---

## Framework: LangChain AgentExecutor vs LangGraph vs custom loop

### Option A — LangChain `AgentExecutor` (ReAct)

The agent receives all tools and, at each step, the LLM decides which tool to call next (Reason → Act → Observe loop).

**Discarded because:**
- The workflow of US3 has a fixed structure: always decompose, then generate, then validate. A ReAct agent could call tools out of order or skip steps.
- `AgentExecutor` is in maintenance mode; LangChain itself recommends LangGraph for all new agent work.
- Termination and constraint validation are non-deterministic — the LLM decides when it is "done", which is inappropriate for a budget-enforcement guardrail.

### Option B — Custom ReAct loop with `instructor`

Implement the tool-calling loop manually: call the LLM with function definitions, parse tool calls, execute them, feed results back, repeat until the LLM stops.

**Discarded as the primary approach because:**
- Routing logic, cycle detection (adjust → validate → adjust), and termination conditions all need to be implemented manually. LangGraph handles these with typed edges.
- Acceptable for a single-tool agent; for a multi-step workflow with conditional retry loops, the custom loop becomes a state machine that LangGraph already is.
- The code becomes hard to reason about and test as the number of states grows.

### Option C — LlamaIndex `AgentRunner`

LlamaIndex has its own agent abstraction oriented around query pipelines and RAG.

**Discarded because:**
- LlamaIndex's strength is retrieval, not orchestration. Its agent primitives are less expressive than LangGraph for workflows with conditional branching.
- Mixing LlamaIndex as both the RAG backend (US2) and the agent framework would tightly couple two concerns.

### Option D — LangGraph (chosen)

LangGraph models the agent as an explicit state graph. Each node is a Python function. Edges encode transitions. Conditional edges encode branching logic. The shared `PlannerState` TypedDict flows through the graph.

**Chosen because:**
- The workflow has a clear structure with a validation loop — exactly what a state graph models cleanly.
- Termination is explicit: a conditional edge routes to `END` when no violations are found, or to `salvage` when max attempts are exhausted. The LLM does not decide when to stop.
- Constraint validation (`validate_constraints`) is always a deterministic Python node — it is not a tool the LLM can decide to call or skip.
- The graph is auditable: the structure can be drawn, inspected, and explained step by step.
- It is a widely adopted framework for deterministic, stateful agent orchestration..

---

## Graph structure

```
START
  │
  ▼
retrieve_context      ← RAG: queries uploaded documents; returns "" if none exist
  │
  ▼
decompose_goal        ← LLM: breaks the goal into 3–7 concrete subtopics
  │
  ▼
generate_tasks        ← reuses TaskGenerator (US1) with subtopics in extra_instructions
  │
  ▼
validate_constraints  ← Python: checks total hours ≤ remaining_budget × tolerance
  │
  ├─ valid ──────────► END
  ├─ invalid, retry ──► adjust_plan  ← LLM: receives current tasks AND violations
  │                         │
  │                         └──► validate_constraints  (loop)
  └─ invalid, exhausted ──► salvage  ← Python: trims to valid subset
                                │
                                └──► END
```

---

## Key design decisions

### Constraint validation is a graph node, not a tool

The acceptance criteria require that constraints are always enforced. If `validate_constraints` were an LLM-callable tool (as in a ReAct agent), the LLM might skip it. Making it an unconditional graph node guarantees it always runs after generation and after each adjustment.

### `adjust_plan` receives both current tasks and violations

The prompt explicitly includes:
- The full task list (title, hours, rationale) so the LLM knows what it is working with.
- The exact constraint violations to fix.

Without the current task list, the LLM would have to invent tasks from scratch. Without the violations, it would not know what to change. Both are required for informed, targeted adjustments.

### `generate_tasks` reuses `TaskGenerator` from US1

Rather than writing a new LLM call for task generation, the agent passes the decomposed subtopics as `extra_instructions` to the existing `TaskGenerator`. This means the agent inherits US1's semantic validation, retry logic, and salvage mechanism for free. The agent's outer loop handles budget-level validation; US1's inner loop handles per-task structural validation.

### RAG context is optional

`retrieve_context` checks whether the plan has uploaded documents. If not, it returns an empty string and the graph continues without modifying the LLM prompts. If documents exist, the retrieved chunks enrich both `decompose_goal` (for better subtopic selection) and `generate_tasks` (for domain-specific task content). The RAG integration reuses the `Retriever` interface from US2 without any changes.

### Salvage instead of hard failure

If the agent exhausts all adjustment attempts, it persists whatever valid subset fits within the budget rather than returning 502. This mirrors the salvage mechanism in US1 and ensures the user always gets some output.

---

## Stub design for testing

The `StubLLMClient` from US1 is extended with two new fabricators:

- `SubtopicList` fabricator: returns three generic subtopics derived from the goal string.
- `AdjustedTaskList` fabricator: trims the current task list to fit within the `hours_budget` passed in the `context` argument.

This allows the full graph (all nodes, all edges, the conditional routing) to execute in tests without any network calls or credentials.

---

## Environment variable

| Variable | Default | Description |
|---|---|---|
| `AGENT_MAX_ATTEMPTS` | `3` | Total attempt count including the initial generation. With the default of 3, the agent makes 1 initial generation and up to 2 adjustment cycles before falling back to salvage. |
| `AGENT_MIN_SUBTOPICS` | `3` | Minimum number of subtopics the decompose step must return. Enforced by Pydantic validator on `SubtopicList`. |
| `AGENT_MAX_SUBTOPICS` | `7` | Maximum number of subtopics allowed. Values above 7 tend to produce generic, repetitive tasks. |

---

## Known limitations and future work

### 1. Synchronous execution

**What it means:** The endpoint blocks the HTTP worker until the full agent graph completes. With a real LLM, this is typically 15–45 seconds depending on the number of retries.

**Why it matters in production:** Each in-flight agent request occupies one uvicorn worker for its entire duration. With a small worker pool and concurrent users, the server saturates quickly. HTTP gateway timeouts (typically 30–60s) can also terminate long-running requests before the agent finishes.

**Production solution:** Enqueue the job in a task queue (Celery + Redis) and return a job ID immediately. The client polls `GET /plans/{id}/agent-jobs/{jobId}` for the result. LangGraph supports checkpointers that persist graph state between executions, enabling resumable agents. This is a large architectural change orthogonal to the agent's correctness and is deferred accordingly.

---

### 2. No progress streaming

**What it means:** The user sees a loading spinner with no feedback until the agent completes. There is no indication of which node is running or how many subtopics were identified.

**The solution:** LangGraph supports `graph.stream()`, which emits an event after each node completes. Combined with Server-Sent Events on the HTTP layer, the frontend could render:

```
⟳ Retrieving context from documents...
✓ Goal decomposed: Fundamentals · Core concepts · Practical application
⟳ Generating tasks...
✓ 8 tasks generated — validating constraints...
✓ Constraints satisfied
```

**Trade-off:** It requires changing the endpoint from returning JSON to returning `text/event-stream` and updating the frontend to consume an `EventSource`. The streaming implementation is deferred until the async job queue (limitation 1) is in place, as both changes belong to the same architectural upgrade.

---

### 3. Graph recompiled on every request

**What it means:** `PlannerGraph.build()` calls `graph.compile()` on every request. Compilation builds the execution plan and validates the graph structure — it has non-trivial overhead even if small relative to LLM latency.

**Why caching is non-trivial:** The compiled graph's nodes are bound methods of `PlannerGraph`, which capture request-scoped dependencies (`DocumentRepository`, `LLMClient`). Caching the compiled graph would cache those dependencies too, breaking request isolation.

**The correct solution:** Separate graph structure (static, compiled once at startup) from runtime dependencies (injected per-request via LangGraph's `RunnableConfig`). This is the pattern LangGraph recommends for production:

```python
compiled_graph = build_static_graph()  # once at startup

# per request:
compiled_graph.invoke(state, config={"configurable": {"doc_repo": ..., "llm": ...}})
```

**Trade-off:** Refactoring requires changing node functions from bound methods to free functions that read dependencies from `RunnableConfig`, which changes the internal API of `PlannerGraph` significantly. Given that `graph.compile()` overhead is negligible compared to LLM call latency, the more impactful fix is the async job queue (limitation 1), not compilation caching.

---

### 4. Subtopic coherence not validated

**What it means:** The agent trusts the LLM's `decompose_goal` output without verifying that the subtopics are actually relevant to the original goal. An adversarial prompt or a poorly-performing model could return subtopics that are off-topic, and `generate_tasks` would generate tasks for those irrelevant subtopics.

**Existing mitigation:** The `decompose_goal` system prompt explicitly instructs the model to produce subtopics that "together cover the goal comprehensively". This is instructional, not enforced.

**The solution:** Add a `validate_subtopics` node between `decompose_goal` and `generate_tasks` that checks structural constraints deterministically (non-empty list, at least 2 distinct items, each subtopic is a non-empty string). Semantic coherence validation would require an additional LLM call, which adds latency and a new failure mode without a clear definition of "coherent".

**Trade-off:** Structural checks (non-empty, distinct items) are already partially enforced by the `SubtopicList` Pydantic schema. Semantic validation requires defining a measurable criterion for "relevance to the goal" — without that definition, any implementation would be arbitrary.

---

### 5. Single LLM call covers all subtopics

**What it means:** `generate_tasks` passes all subtopics as `extra_instructions` in a single `TaskGenerator` call. The LLM may cover some subtopics more thoroughly than others, or even skip low-priority ones.

**Alternative approach:** Call `TaskGenerator` once per subtopic with a proportional hours budget (`total_budget / num_subtopics`). This guarantees at least one task per subtopic.

**Trade-off:** Per-subtopic generation produces N LLM calls instead of 1 (N = number of subtopics, typically 3–7). The current single-call approach is efficient and the `adjust_plan` node mitigates coverage gaps by re-prompting with the required subtopics list. For production with strict coverage requirements, per-subtopic generation is the better choice.

**Trade-off:** The single-call approach is efficient and the `adjust_plan` node mitigates coverage gaps. Per-subtopic generation is a quality enhancement for future work when strict per-subtopic coverage is required.
