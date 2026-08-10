# Orion Architecture

## Overview

Orion is a workflow orchestration framework built on LangGraph.

It separates planning, execution, completion evaluation, replanning, and response synthesis into independent workflow nodes.

---

## High-Level Architecture

```
                    START
                      │
                      ▼
                  Agent Node
                      │
                      ▼
                 Planner Node
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
     Error Handler          Executor Node
                                  │
                                  ▼
                           Completion Node
                                  │
         ┌──────────────┬──────────────┬──────────────┐
         │              │              │              │
         ▼              ▼              ▼              ▼
     Executor      Replanner     Synthesizer    Error Handler
                                              │
                                              ▼
                                             END
```

---

## Workflow Components

| Component | Responsibility |
|-----------|----------------|
| Agent | Receives user requests |
| Planner | Creates execution plans |
| Executor | Executes tools |
| Completion | Evaluates workflow state |
| Replanner | Generates additional work |
| Synthesizer | Produces final response |
| Error Handler | Handles failures |

---

## Supporting Components

- Tool Registry
- Validator
- Shared Types
- AgentState
- Runtime Models

---

## Documentation

- planner.md
- executor.md
- completion.md
- replanner.md
- validator.md
- workflow.md
- state.md
- graph.md

---

## Architecture Decision Records

See:

```
docs/adr/
```

for the architectural decisions that shaped Orion.