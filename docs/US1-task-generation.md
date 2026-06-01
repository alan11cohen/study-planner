# US1 — Task Generation: Technical Decisions

## What it does

`POST /plans/{id}/generate-tasks` generates a structured list of study tasks for a plan using an LLM. It:

1. Computes the available hours budget from the plan's weekly commitment and target date.
2. Builds a prompt that includes the goal, time constraints, and any existing tasks to avoid duplicating.
3. Calls the LLM using native structured output to parse the response directly into a typed schema.
4. Validates the output with a multi-layered deterministic checker.
5. On validation failure, re-prompts the LLM with the exact errors and retries up to `TASKGEN_MAX_ATTEMPTS` times.
6. If all attempts fail, persists the largest valid subset (salvage) rather than returning an error.

---

## Structured output: native OpenAI vs `instructor`

### Option A — `instructor`

`instructor` patches the OpenAI client to add automatic retries, Pydantic validation, and re-prompting when the model returns invalid output.

**Discarded because:**
- It adds a dependency that hides retry and validation logic the implementation needs to own explicitly.
- The retry loop must inject domain-specific validation errors (task count, hours budget, title overlap) — not just schema errors. `instructor` only retries on schema failures.
- Owning the retry loop explicitly makes the failure path transparent and testable.

### Option B — LangChain (`langchain-openai` + `with_structured_output`)

LangChain provides a unified interface over many LLM providers with built-in structured output via `.with_structured_output(schema)`.

**Discarded because:**
- Significant dependency weight (~15 transitive packages) for a feature that is a thin wrapper over the same OpenAI API.
- Retry and error handling are buried inside chain internals, making failure paths opaque.
- No added value for a single-provider project where the abstraction is already handled by `LLMClient`.

### Option C — Native OpenAI structured output (chosen)

`beta.chat.completions.parse` accepts a Pydantic schema as `response_format`. The API guarantees the response conforms to the schema or returns a refusal.

**Chosen because:**
- No additional dependency. The retry loop, validation, and re-prompting logic are explicit and fully controlled by the application.
- Structural validation (schema conformance) is handled by the API. The application layer focuses on semantic validation (budget, uniqueness, hours realism).
- The approach is transparent: every retry includes the exact error messages from the previous attempt, injected directly into the user prompt.

---

## Validation layers

Validation runs after every LLM response. It is deterministic Python — no LLM involved. Errors are collected and returned as a structured report.

| Layer | What it checks |
|---|---|
| Task count | At least `TASKGEN_MIN_TASKS`, at most `TASKGEN_MAX_TASKS` |
| Title validity | Non-empty, under 200 characters |
| Estimated hours per task | Positive finite number within `[TASKGEN_MIN_TASK_HOURS, hours_per_week × TASKGEN_MAX_TASK_HOURS_RATIO]` |
| Non-empty rationale | Every task must have a non-empty rationale string |
| Unique titles (exact) | Case-insensitive exact match within the batch and against existing plan tasks |
| Unique titles (semantic) | Overlap coefficient on content words (stop words removed) ≥ 0.6 is rejected as a near-duplicate |
| Budget | Sum of `estimated_hours` ≤ `remaining_budget × TASKGEN_BUDGET_TOLERANCE` |
| Uniform hours (warning) | If ≥ 60% of tasks share the same `estimated_hours`, a warning is emitted |
| Under-utilisation (warning) | If total hours < 40% of remaining budget, a warning is emitted |

### Retry loop

On any validation error, the errors are appended to the next prompt:

```
Your previous attempt was rejected by validation. Fix ALL of these issues and try again:
- Task 3 ('Review key concepts') overlaps with an already-existing task ('Review fundamental concepts')...
```

The LLM receives the exact constraint it violated and is asked to fix it. This self-correction loop runs up to `TASKGEN_MAX_ATTEMPTS` times.

### Salvage

If all attempts are exhausted, the generator keeps every task from the last response that individually passes structural checks and fits within the remaining budget. If at least one task is kept, it is persisted with a warning. If no tasks survive, a `TaskGenerationError` is raised and the endpoint returns 502.

---

## Budget calculation

`PlanContext.hours_budget()` computes total available hours:

- With `target_date`: `hours_per_week × (days_until_target / 7)`
- Without `target_date`: `hours_per_week × TASKGEN_DEFAULT_HORIZON_WEEKS`

`PlanContext.remaining_budget()` subtracts `existing_hours` (hours already allocated to existing tasks in the plan). This ensures that appended task batches do not over-allocate the plan's total time.

---

## LLM abstraction

All LLM calls go through `LLMClient.parse()`, a single-method interface:

```python
def parse(self, *, system: str, user: str, schema: type[T], ...) -> T: ...
```

Business logic (`TaskGenerator`, `ChatService`, `PlannerGraph`) depends only on this interface. The concrete implementation (`OpenAIClient`) is injected via FastAPI's dependency system. `StubLLMClient` provides a deterministic offline implementation used in all tests.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `auto` | `auto` selects `openai` when `OPENAI_API_KEY` is set, `stub` otherwise. |
| `OPENAI_API_KEY` | _(empty)_ | Required for production use. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat completion model. |
| `LLM_TIMEOUT_SECONDS` | `30.0` | HTTP timeout for OpenAI requests. |
| `TASKGEN_MAX_ATTEMPTS` | `3` | Maximum LLM call attempts per generation request, including the initial attempt. |
| `TASKGEN_MIN_TASKS` | `1` | Minimum tasks the LLM must return. |
| `TASKGEN_MAX_TASKS` | `20` | Maximum tasks allowed in a single generation. |
| `TASKGEN_MIN_TASK_HOURS` | `0.5` | Minimum hours per task. Tasks below this are unrealistically short. |
| `TASKGEN_MAX_TASK_HOURS_RATIO` | `1.5` | A single task cannot exceed `hours_per_week × ratio`. Prevents tasks larger than one week of work. |
| `TASKGEN_BUDGET_TOLERANCE` | `1.25` | Total hours may exceed the budget by up to 25% to allow for slight over-estimation. |
| `TASKGEN_DEFAULT_HORIZON_WEEKS` | `8` | Planning horizon used when the plan has no target date. |
