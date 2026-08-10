# Completion Node

## Purpose

The Completion Node evaluates the current execution state of the workflow after one or more steps have been executed.

It determines the next action for the workflow by returning a `CompletionStatus`.

Unlike the Executor, it does not execute tools. Its responsibility is only to evaluate workflow state.

---

# Responsibilities

The Completion Node:

- Inspects tool execution results
- Classifies workflow state
- Detects recoverable failures
- Detects non-recoverable failures
- Determines whether more planned work remains
- Returns a `CompletionStatus`

---

# Completion Status

The Completion Node returns one of four states.

## COMPLETE

All planned steps have completed successfully.

The workflow can proceed to the Synthesizer.

---

## CONTINUE

The current execution plan still contains unexecuted steps.

The Executor should continue executing the remaining steps.

---

## REPLAN

A recoverable failure has been detected.

Examples include:

- Timeout
- Temporary infrastructure failure
- Transient API failure

The workflow should invoke the Replanner to generate additional execution steps.

---

## FAILED

A non-recoverable failure has occurred.

Examples include:

- Validation failure
- Invalid tool
- Unsupported operation

The workflow should terminate through the Error Handler.

---

# Workflow

```
Executor
    │
    ▼
Completion
    │
    ├───────────────┐
    │               │
 COMPLETE       CONTINUE
    │               │
    ▼               ▼
Synthesizer     Executor

        REPLAN
           │
           ▼
      Replanner

        FAILED
           │
           ▼
     Error Handler
```

---

# Decision Logic

The Completion Node evaluates execution results in the following order:

1. Recoverable failures
2. Non-recoverable failures
3. Remaining planned steps
4. Workflow completion

This ordering ensures that recoverable errors are handled before considering the workflow complete.

---

# Current Limitation

The current implementation preserves failed execution history.

When the Replanner generates additional steps, failed steps remain part of the workflow history.

As a result, recoverable failures continue to be detected during subsequent completion checks.

---

# Future Enhancement

Sprint 10 will introduce **step supersession**.

Instead of leaving recoverable failed steps active, they will be marked as superseded once replacement steps have been generated.

This will allow the Completion Node to distinguish between:

- Active failures
- Historical failures

while preserving the execution history.