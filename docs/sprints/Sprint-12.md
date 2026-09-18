````markdown
# Sprint 12 - Multi-Agent Architecture

**Status:** Implementation in progress - initial multi-agent runtime integration complete

---

## Baseline

Before Sprint 12 implementation:

- Existing test suite: **156 passed**
- Sprint 11 visualization: complete
- Sprint 11 committed and pushed

Current Sprint 12 status:

- Agent domain model: complete
- Agent runtime boundary: complete
- Initial workflow state integration: complete
- Root Supervisor AgentTask creation: complete
- Planner and Replanner integration: complete
- Executor agent-task association: complete
- Agent task/message persistence: complete
- Full regression suite: **180 passed**
- Explicit agent-to-agent delegation: not yet implemented
- Agent-specific event extensions: not yet implemented
- Agent visualization: deferred

---

## 1. Sprint Objective

Extend Orion from a single-agent, planner-driven workflow runtime into a
multi-agent runtime while preserving the existing execution infrastructure.

The multi-agent architecture must build on the capabilities already implemented
in Orion rather than creating a second, parallel execution framework.

The existing Orion workflow remains responsible for:

- Planning
- Tool execution
- Dependency management
- Parallel execution
- Retries
- Timeouts
- Approvals
- Conditional execution
- Failure handling
- Replanning
- Persistence and resume
- Execution history
- Workflow visualization

The new agent layer provides:

- Agent identity and specialization
- Task delegation
- Agent-to-agent communication
- Agent-specific reasoning
- Coordination between agents

---

## 2. Core Architectural Principle

> **Agents provide specialized reasoning and delegation; Orion's existing
> workflow engine remains responsible for execution, reliability, persistence,
> and lifecycle.**

Agents are logical reasoning/delegation entities.

They are **not separate LangGraph execution graphs** and they do not contain
their own copies of the Executor, retry system, persistence system, or workflow
engine.

---

## 3. Target Architecture

```text
                         USER
                           |
                           v
                    +-------------+
                    | Supervisor  |
                    |    Agent    |
                    +------+------+
                           |
                     AgentTask(s)
                           |
            +--------------+--------------+
            |              |              |
            v              v              v
       Research        Analysis       Calculation
        Agent           Agent           Agent
            |              |              |
         planning       planning       planning
            |              |              |
         PlanSteps      PlanSteps      PlanSteps
            +--------------+--------------+
                           |
                           v
                    ORION EXECUTOR
                           |
                           v
                  Execution Results
                           |
                  +--------+--------+
                  |                 |
                  v                 v
              Agent(s)          Replanner
                  |                 |
                  +--------+--------+
                           |
                           v
                      Synthesizer
                           |
                           v
                          USER
````

---

## 4. Definition of an Agent

An Agent is a specialized reasoning component with:

* Identity
* Name
* Role
* Instructions
* Access to defined capabilities

Example:

```text
ResearchAgent
    role = research
    instructions = research-focused

AnalysisAgent
    role = analysis
    instructions = analysis-focused

CalculationAgent
    role = calculation
    instructions = calculation-focused
```

An Agent is not required to own a separate execution engine.

There will initially be no special SupervisorAgent class.

The Supervisor will be represented as an ordinary AgentDefinition with the
special role of being the root coordinating agent for a workflow.

---

## 5. AgentDefinition

AgentDefinition describes an available agent.

Initial fields:

```text
id
name
role
instructions
```

Example:

```text
AgentDefinition(
    id="research",
    name="Research Agent",
    role="research",
    instructions="Research the assigned subject and organize the findings."
)
```

AgentDefinition should contain configuration and identity, not mutable
execution state.

---

## 6. AgentTask

AgentTask is the fundamental unit of agent delegation.

When one agent asks another agent to perform work, it creates an AgentTask.

Conceptual structure:

```text
AgentTask
    task_id
    parent_task_id
    agent_id
    request
    status
    result
    metadata
```

Example:

```text
Supervisor
    |
    +-- AgentTask
            agent_id = "research"
            request = "Research hybrid cars available in India."
```

---

## 7. AgentTask Hierarchy

AgentTasks form a delegation tree.

Example:

```text
T1 Supervisor
|
+-- T2 Research Agent
|     |
|     +-- T4 Calculation Agent
|
+-- T3 Analysis Agent
```

parent_task_id represents the delegation relationship.

The AgentTask hierarchy is deliberately separate from the PlanStep dependency
graph.

---

## 8. AgentTask Lifecycle

Initial lifecycle:

```text
CREATED
   |
   v
ASSIGNED
   |
   v
RUNNING
   |
   +----------> COMPLETED
   |
   +----------> FAILED
   |
   +----------> CANCELLED
```

A task is considered complete when the responsible agent determines that the
assigned objective has been fulfilled.

Completion of an individual tool execution does not by itself mean that the
AgentTask is complete.

---

## 9. AgentTask and PlanStep

AgentTask and PlanStep represent different levels of work.

|                   | AgentTask                 | PlanStep                 |
| ----------------- | ------------------------- | ------------------------ |
| Represents        | Work assigned to an agent | Concrete executable work |
| Owner             | Agent                     | Orion Executor           |
| Contains          | Objective/request         | Tool and tool input      |
| Can delegate      | Yes                       | No                       |
| Executes tools    | Indirectly                | Yes                      |
| Hierarchy         | Parent/child task tree    | Dependency graph         |
| Execution history | Through associated work   | ExecutionRecord          |

The intended relationship is:

```text
AgentTask
    |
    v
Agent reasoning
    |
    +----> AgentTask(s)
    |
    +----> PlanStep(s)
                 |
                 v
             Executor
```

An AgentTask should not directly contain PlanSteps as its primary abstraction.

---

## 10. Agent-to-Agent Delegation

Any agent may delegate work to another registered agent.

Example:

```text
Supervisor
    |
    +----> Research Agent
                |
                +----> Calculation Agent
```

Delegation is represented through an AgentTask, not through direct calls from
one agent object to another.

The delegating agent creates a task specifying the target agent.

Conceptually:

```text
Research Agent
    |
    | creates AgentTask
    v
AgentRegistry
    |
    v
Calculation Agent
```

This avoids tight coupling between individual agents.

---

## 11. AgentTask Execution Model

The initial AgentTask API will be synchronous.

Conceptually:

```text
Supervisor
    |
    v
Research Agent
    |
    v
result
    |
    v
Supervisor continues
```

The architecture should not prevent future concurrent or asynchronous
AgentTasks.

Orion already supports parallel execution at the PlanStep level, so agent-level
concurrency can be introduced later without redesigning the fundamental
AgentTask model.

---

## 12. Agent Reasoning Model

Orion remains planner-driven.

The initial model is:

```text
AgentTask
    |
    v
Agent reasoning/context
    |
    v
Planner
    |
    v
PlanStep(s)
    |
    v
Executor
    |
    v
Results
    |
    v
Agent reasoning
```

Agents should not initially implement independent autonomous tool-execution
loops.

The existing Planner and Executor remain the primary planning and execution
mechanisms.

---

## 13. Planner Boundary

The existing Planner should remain reusable.

An agent's specialization should be provided through its definition,
instructions, role, and task context rather than by creating a separate planner
implementation for every agent.

Conceptually:

```text
AgentDefinition
       +
AgentTask
       |
       v
    Planner
       |
       v
   PlanStep(s)
```

The exact mechanism for supplying agent-specific planning context will be
determined during implementation.

---

## 14. Executor Boundary

The Executor remains generic and should remain unaware of individual agent
implementations wherever possible.

The Executor continues to handle:

* Tool resolution
* Dependency checking
* Parallel execution
* Retries
* Timeouts
* Approvals
* Conditions
* Reference resolution
* Context updates
* Execution records
* Checkpointing
* Persistence

The Executor should not become an agent coordinator.

---

## 15. Failure Handling

Agent failures should use Orion's existing failure and replanning mechanisms
rather than creating a separate agent-specific retry framework.

Conceptually:

```text
Tool failure
    |
    v
Executor
    |
    v
FailureReason / ExecutionRecord
    |
    v
Completion / Replanner
    |
    v
Agent receives result
    |
    +----> continue
    +----> replan
    +----> use another tool
    +----> delegate
    +----> fail task
```

Existing concepts such as:

* FailureReason
* ExecutionRecord
* RetryError
* CompletionStatus
* Replanner

remain authoritative for workflow execution failures.

---

## 16. AgentMessage

Agent-to-agent communication will use an explicit message abstraction.

Initial conceptual structure:

```text
AgentMessage
    message_id
    sender
    recipient
    content
    task_id
    correlation_id
```

task_id identifies the task to which the message relates.

correlation_id identifies the larger request/conversation chain and becomes
important when multiple agent tasks are active.

Agents should communicate through messages and tasks rather than directly
modifying another agent's state.

---

## 17. Agent Memory

Agents may eventually have private working memory in addition to shared
workflow context.

For Sprint 12, memory will remain minimal.

The workflow remains the authoritative source for:

* PlanSteps
* Tool results
* Execution records
* Workflow context
* Completion status
* Persistence

No complex long-term or vector memory system is part of this sprint.

---

## 18. AgentRegistry

Orion already has a global Tool Registry.

A corresponding Agent Registry will provide discovery of available agents.

Initial operations:

```text
register_agent()
get_agent()
list_agents()
clear_registry()
```

Conceptually:

```text
AGENT_REGISTRY
    |
    +-- supervisor
    +-- research
    +-- analysis
    +-- calculation
```

The registry is independent of the Tool Registry.

---

## 19. Proposed Repository Structure

Initial new package:

```text
agents/
├── __init__.py
├── models.py
├── task.py
├── message.py
├── registry.py
└── runtime.py
```

Responsibilities:

### agents/models.py

* AgentDefinition
* Agent task status enum, if appropriate

### agents/task.py

* AgentTask

### agents/message.py

* AgentMessage

### agents/registry.py

* Agent registry and lookup functions

### agents/runtime.py

* AgentTask processing
* Agent reasoning/planning integration
* Agent delegation
* Agent result handling

The existing top-level agent.py currently contains only a placeholder
agent_node(). It should not accumulate the complete multi-agent
implementation.

Its eventual role will be determined when the workflow graph is integrated.

---

## 20. AgentState Integration

The existing AgentState remains workflow-level state.

Agent definitions should not be duplicated into every workflow state.

The intended separation is:

```text
AgentRegistry
    |
    +-- available AgentDefinitions

AgentState
    |
    +-- AgentTasks belonging to this workflow
    +-- AgentMessages belonging to this workflow
```

Likely state additions:

```text
agent_tasks
agent_messages
```

The exact types and serialization format will be established after the
AgentTask and AgentMessage models are implemented.

---

## 21. Event System

The current event system is workflow/step oriented.

Current WorkflowEvent contains:

```text
type
timestamp
step_id
tool
payload
```

Current event types include:

```text
WORKFLOW_STARTED
WORKFLOW_COMPLETED
STEP_STARTED
STEP_COMPLETED
STEP_FAILED
STEP_SKIPPED
```

Agent-specific events should not be forced into the existing event system before
the AgentTask and AgentMessage semantics are established.

Potential future events include:

```text
AGENT_TASK_CREATED
AGENT_TASK_STARTED
AGENT_TASK_COMPLETED
AGENT_TASK_FAILED
AGENT_MESSAGE
```

These are design candidates, not yet implementation decisions.

---

## 22. Persistence

Agent-specific persistence will be added only after the AgentTask and
AgentMessage models are stable.

Eventually persistence should support:

```text
agent_tasks
agent_messages
```

alongside the existing workflow information.

The existing persistence and resume architecture remains authoritative.

Required eventual behavior:

```text
create AgentTask
      |
      v
persist workflow
      |
      v
load workflow
      |
      v
resume
      |
      v
continue AgentTask
```

---

## 23. Visualization

Sprint 11 established the Runtime Workflow Graph.

Multi-agent visualization should extend that model rather than create a
separate visualization architecture.

Eventually the system should be able to show both:

```text
Agent delegation hierarchy

Supervisor
|
+-- Research Agent
|
+-- Analysis Agent
```

and:

```text
Execution graph

Research Agent
    |
    +-- Step 1
    +-- Step 2

Analysis Agent
    |
    +-- Step 3
```

The exact visualization changes are deferred until the agent execution model is
stable.

---

## 24. Implementation Phases

### Phase 1 - Agent Domain Model

Create:

```text
agents/
├── __init__.py
├── models.py
├── task.py
├── message.py
└── registry.py
```

Implement and test:

* AgentDefinition
* AgentTask
* AgentTaskStatus
* AgentMessage
* AgentRegistry

No existing workflow behavior should change in this phase.

---

### Phase 2 - Agent Runtime

Create:

```text
agents/runtime.py
```

The runtime should initially support:

1. Receiving an AgentTask
2. Resolving its AgentDefinition
3. Constructing agent-specific planning context
4. Generating PlanSteps
5. Integrating with existing Orion execution
6. Determining task completion
7. Returning the result

The exact integration with the existing LangGraph workflow must be designed
before implementation.

---

### Phase 3 - Workflow State Integration

Add workflow-level storage for:

```text
agent_tasks
agent_messages
```

Do not duplicate AgentDefinitions in workflow state.

Add tests for:

* task creation
* task state transitions
* message storage
* state isolation between workflows

---

### Phase 4 - Supervisor

Register:

```text
supervisor
```

as a normal AgentDefinition.

The Supervisor should initially support explicit delegation to another agent.

First target behavior:

```text
User request
    |
    v
Supervisor
    |
    v
AgentTask
    |
    v
Research Agent
```

---

### Phase 5 - Workflow Graph Integration

After the AgentTask runtime is proven independently, integrate it with:

```text
agent.py
workflow/nodes.py
workflow/graph.py
```

The exact graph topology should be determined from the working AgentTask
runtime rather than assumed in advance.

The existing Planner, Executor, Replanner, and Synthesizer should remain
functional.

---

### Phase 6 - Agent-to-Agent Delegation

Implement:

```text
Supervisor
    |
    v
Research Agent
    |
    v
Calculation Agent
```

Verify that:

* child tasks have the correct parent_task_id
* results return to the parent
* task status transitions correctly
* multiple levels of delegation are supported
* agents remain loosely coupled

---

### Phase 7 - Events and Persistence

After task and message semantics are stable:

* extend event types if required
* extend WorkflowEvent if required
* persist AgentTasks
* persist AgentMessages
* test resume behavior

Do not add unnecessary event or persistence fields before their semantics are
established.

---

### Phase 8 - Visualization

Extend the existing visualization model to represent agent and task
information where useful.

Do not create a second visualization framework.

---

### Phase 9 - Regression and Stabilization

Run:

```bat
pytest -q
```

All existing tests must continue to pass.

Regression areas include:

* Planner
* Executor
* Parallel execution
* Retries
* Failures
* Replanning
* Persistence
* Resume
* Visualization

Add the multi-agent test suite alongside the existing tests.

---

## 25. Initial Test Structure

Proposed tests:

```text
tests/
├── test_agents_models.py
├── test_agents_task.py
├── test_agents_message.py
├── test_agents_registry.py
├── test_agents_runtime.py
├── test_agents_delegation.py
├── test_agents_persistence.py
└── test_agents_integration.py
```

The first architectural proof should be deliberately small:

```text
Registered Supervisor
        |
        v
creates AgentTask
        |
        v
Registered Research Agent
        |
        v
creates normal Orion PlanSteps
        |
        v
existing Orion Executor
        |
        v
execution result
```

If this works without duplicating execution infrastructure, the core
multi-agent architecture is validated.

---

## 26. Explicit Non-Goals for Sprint 12

The following are not part of the initial implementation:

* Separate LangGraph workflow for every agent
* Agent-specific Executor
* Independent retry framework
* Distributed agents
* Message queues
* Database-backed agent coordination
* Complex cancellation
* Long-term or vector memory
* Autonomous infinite agent loops
* Multiple independent persistence systems
* A separate visualization architecture

These may be considered in later sprints if required.

---

## 27. Architectural Constraints

The following constraints should be preserved throughout implementation:

1. **Do not duplicate the existing Executor.**

2. **Do not make agents directly execute registered tools.**

3. **Do not make individual agents tightly coupled to other agent classes.**

4. **Use AgentTask for delegation.**

5. **Use AgentMessage for agent communication.**

6. **Keep AgentDefinitions separate from workflow state.**

7. **Keep AgentTask hierarchy separate from PlanStep dependency hierarchy.**

8. **Keep existing Planner, Executor, and Replanner responsibilities intact.**

9. **Do not modify persistence or events prematurely; establish semantics
   first.**

10. **Maintain backward compatibility with existing single-agent workflows
    wherever practical.**

---

## 28. Design Checkpoint

At this point the following architectural decisions are agreed:

* Multi-agent functionality will extend the existing Orion runtime.
* Agents are logical reasoning/delegation entities.
* Agents are not separate LangGraph workflows.
* Supervisor is an ordinary AgentDefinition.
* Any agent may delegate to another agent.
* AgentTask is the unit of delegation.
* PlanStep remains the unit of concrete tool execution.
* Plan ownership is hybrid.
* Orion Executor remains the common execution engine.
* Orion remains planner-driven.
* AgentTask API is initially synchronous.
* Agent memory is initially minimal.
* AgentTask hierarchy is separate from the execution dependency graph.
* AgentRegistry provides agent discovery.
* AgentMessage provides agent-to-agent communication.
* Persistence and event changes follow the core model rather than precede it.
* Visualization will extend the existing Sprint 11 architecture.

### Current Implementation Checkpoint

The following implementation work is now complete:

- Agent domain model has been implemented.
- `AgentRuntime` has been introduced as the reusable agent execution boundary.
- `PlanningService` has been extracted from the Planner node.
- A root Supervisor AgentTask is created and reused across workflow resume.
- AgentTasks and AgentMessages are represented in workflow state.
- `PlanStep` and `ExecutionRecord` carry agent-task association.
- Planner and Replanner output are converted to the canonical runtime `PlanStep`.
- Agent task/message persistence has been integrated.
- Existing Orion execution remains the common execution engine.
- Full regression suite currently passes with **180 tests**.

The following remain intentionally incomplete:

- explicit agent-to-agent delegation
- complete AgentTask completion semantics
- agent-specific event extensions
- agent visualization

**Implementation is in progress.**

````