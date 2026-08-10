# Agent State

## Purpose

`AgentState` is the shared workflow state used by every node in the LangGraph execution pipeline.

Each node reads information from the state and returns updates that LangGraph merges into the workflow state.

---

# Responsibilities

The AgentState stores:

- User messages
- Execution plan
- Tool execution results
- Retrieved documents
- Workflow context
- Execution records
- Completion status
- Errors
- Replanning iteration count

---

# State Fields

| Field | Description |
|--------|-------------|
| messages | Conversation history |
| steps | Current execution plan |
| tool_results | Results returned by executed tools |
| documents | Retrieved RAG documents |
| context | Shared workflow context |
| output | Final structured output |
| execution_records | Execution history |
| completion_status | Current workflow status |
| error | Current OrionError |
| errors | Validation errors |
| iteration | Number of replanning attempts |

---

# Workflow

```
Planner
      │
      ▼
 AgentState
      │
      ▼
 Executor
      │
      ▼
 Completion
      │
      ▼
 Replanner
```

---

# Design Principles

- Single source of truth
- Immutable updates between nodes
- Centralized workflow context
- Easy to extend