# Orion Graphs

Orion uses two different graph concepts.

`Execution Graph` describes how Orion itself runs, while `Runtime Workflow Graph` describes what happened to the user's individual workflow.

## 1. Execution Graph

The execution graph is the LangGraph workflow used to orchestrate Orion.

```text
User Request
      ↓
Agent
      ↓
Planner
      ↓
Executor
      ↓
Completion
      ↓
 ┌────┼─────────┬────────┐
 ↓    ↓         ↓        ↓
CONTINUE REPLAN COMPLETE FAILED
 ↓      ↓
Executor Replanner

```

This graph controls workflow execution.

Its nodes represent workflow orchestration responsibilities such as Agent, Planner, Executor, Completion, Replanner, and Synthesizer.

---

## 2. Runtime Workflow Graph

The runtime workflow graph represents the logical execution plan and its execution history.

It is built from `AgentState`.

Each `PlanStep` becomes a visualization node.

Nodes contain information such as:

- step ID
- tool
- status
- retry count
- duration
- error
- condition
- approval requirement
- replacement relationship

Edges represent:

- dependencies between steps
- replacement relationships

A superseded step remains visible so that execution history is preserved.

---

## Visualization

The runtime workflow graph is independent of the rendering technology.

```text
AgentState
    ↓
VisualizationBuilder
    ↓
WorkflowGraph
    ↓
Renderer
```

The initial renderer is Mermaid.

The visualization layer does not participate in workflow execution.