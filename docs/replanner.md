# Replanner Node

## Purpose

The Replanner Node determines whether additional work is required after the current execution plan has been executed.

It analyzes the workflow state, execution results, and the original user request to decide whether the workflow is complete or whether additional execution steps should be generated.

Unlike the Planner, the Replanner never recreates the entire workflow. Its responsibility is only to generate the **additional work** required to satisfy the user's request.

---

# Responsibilities

The Replanner:

- Reviews completed execution
- Analyzes successful and failed steps
- Examines pending steps
- Uses the original user request as context
- Generates additional execution steps when necessary
- Prevents unnecessary duplication of completed work

---

# Workflow Context

The Replanner receives the following information:

- Original user request
- Current execution plan
- Completed steps
- Failed steps
- Pending steps
- Available tools

This provides the LLM with sufficient context to decide whether further execution is required.

---

# Workflow

```
Completion
      │
      ▼
CompletionStatus

      │
      ▼
   REPLAN
      │
      ▼
 Replanner
      │
      ▼
Additional Steps
      │
      ▼
 Executor
```

---

# Current Behaviour

The Replanner currently appends newly generated steps to the existing execution plan.

Previously executed steps are preserved to maintain a complete execution history.

Successful steps are never recreated.

---

# Current Limitation

Recoverable failed steps remain part of the execution history.

As a result, the Completion Node continues to detect these failures during later workflow evaluations, even after replacement steps have been executed.

This behavior is intentional in the current implementation because execution history is preserved.

---

# Future Enhancement

Sprint 10 will introduce **step supersession**.

Instead of leaving recoverable failed steps active, the Replanner will mark them as superseded once replacement steps have been generated.

This will allow the workflow to:

- Preserve execution history
- Ignore superseded failures
- Complete successfully after replanning
- Support true dynamic replanning

---

# Design Principles

The Replanner follows three important principles:

1. Never recreate successful work.
2. Generate only the additional work required.
3. Preserve execution history for auditing and debugging.