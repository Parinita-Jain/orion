# Orion Workflow

## Overview

Orion executes user requests through a sequence of specialized workflow nodes.

Each node has a single responsibility.

---

# Workflow

```
User Request
      │
      ▼
Agent
      │
      ▼
Planner
      │
      ▼
Executor
      │
      ▼
Completion
      │
      ├──────────────┬───────────────┬──────────────┐
      │              │               │              │
      ▼              ▼               ▼              ▼
CONTINUE         REPLAN         COMPLETE        FAILED
      │              │               │              │
      ▼              ▼               ▼              ▼
Executor      Replanner      Synthesizer    Error Handler
```

---

# Workflow Nodes

## Agent

Receives the user request.

---

## Planner

Creates an execution plan.

---

## Executor

Executes workflow steps.

---

## Completion

Evaluates workflow state.

---

## Replanner

Generates additional execution steps when required.

---

## Synthesizer

Produces the final response.

---

## Error Handler

Processes workflow failures.