# Sprint 13 --- Streaming Execution

## Objective

Introduce a Python runtime event-stream abstraction for Orion.

The stream will expose workflow/runtime events while the existing
LangGraph workflow is executing, without changing the Executor or
replacing the existing EventBus.

This sprint implements **workflow event streaming**, not LLM token
streaming.

------------------------------------------------------------------------

## Architecture

``` text
                    Workflow
                       │
                       ▼
                  app.invoke()
                       │
                       ▼
                  EventBus
                       │
                 stream listener
                       │
                       ▼
                  Queue[Event]
                       │
                       ▼
                 WorkflowStream
                       │
                       ▼
                    caller
```

The workflow continues to execute through the existing:

``` python
app.invoke(state)
```

path.

`WorkflowStream` runs that invocation in a background thread and exposes
events through a thread-safe queue.

------------------------------------------------------------------------

# Phase 1 --- Streaming Abstraction

Create:

``` text
runtime/stream.py
```

The public API is:

``` python
stream = stream_workflow(state)

for event in stream:
    print(event)

final_state = stream.result
```

`WorkflowStream` should:

-   implement an iterator over `WorkflowEvent`
-   execute the workflow in a background thread
-   expose events as they are emitted
-   retain the final workflow state
-   expose worker errors
-   expose whether execution has completed

The existing workflow execution mechanism remains unchanged.

------------------------------------------------------------------------

# Phase 2 --- EventBus → Queue Bridge

Do **not** modify `EventBus`.

`EventBus` remains a synchronous publisher:

``` text
emit(event)
    ↓
listener(event)
```

`WorkflowStream` attaches a listener which places every event into:

``` python
queue.Queue
```

Conceptually:

``` text
EventBus
    │
    ▼
stream listener
    │
    ▼
Queue[WorkflowEvent]
    │
    ▼
WorkflowStream.__next__()
```

The queue provides thread-safe communication between the workflow thread
and the caller.

------------------------------------------------------------------------

# Phase 3 --- Background Workflow Execution

A streamed workflow must not block the caller while:

``` python
app.invoke(state)
```

is executing.

Therefore:

``` text
Caller thread
     │
     │ consumes events
     ▼
   Queue
     ▲
     │
Background thread
     │
     ▼
app.invoke(state)
```

Each streamed execution receives its own `EventBus`.

For example:

``` text
Workflow A → EventBus A → Stream A

Workflow B → EventBus B → Stream B
```

This prevents events from different workflows from leaking into one
another.

Do not add `unsubscribe()` to `EventBus` for this sprint.

------------------------------------------------------------------------

# Phase 4 --- Result and Error Lifecycle

Streaming provides workflow progress but does not replace the normal
workflow result.

After execution:

``` python
stream.result
```

contains the final LangGraph state.

Before execution finishes:

``` python
stream.result
```

may be:

``` python
None
```

Worker exceptions must not disappear silently.

Expose them through:

``` python
stream.error
```

The stream should continue to provide already-produced events and then
terminate cleanly.

The caller can inspect:

``` python
if stream.error is not None:
    ...
```

------------------------------------------------------------------------

# Phase 5 --- Tests

Add focused tests covering:

### Event delivery

Verify that events emitted by the workflow are delivered through the
stream.

### Real-time delivery

Verify that an event can be consumed before workflow execution has
completed.

### Final result

Verify that:

``` python
stream.result
```

contains the final workflow state after execution.

### Worker error

Verify that a background execution exception is captured in:

``` python
stream.error
```

rather than disappearing.

### Agent events

Verify that existing agent-specific events participate in the stream
automatically.

### Ordering

Verify that events are received in the same order in which the EventBus
emits them.

### Isolation

Verify that separate streaming executions have independent EventBus
instances and do not receive each other's events.

------------------------------------------------------------------------

# Phase 6 --- Resume + Streaming Tests

Streaming resume must use the same persistence semantics already
established by Orion.

Existing:

``` python
resume_workflow(workflow_id)
```

remains unchanged.

The streaming resume path must:

1.  Load the persisted workflow.
2.  Reconstruct runtime-only state.
3.  Mark the workflow as resumed.
4.  Give the streamed execution its own EventBus.
5.  Execute through the existing:

``` python
app.invoke(state)
```

path. 6. Stream the resulting `WorkflowEvent`s. 7. Expose the final
state through:

``` python
stream.result
```

The existing non-streaming resume behavior must remain intact.

Existing resume semantics include:

-   previously successful steps must not execute again
-   remaining steps continue
-   completed workflows must not execute again
-   REPLAN workflows enter the replanner
-   failed original steps must not be re-executed

Streaming must not alter these semantics.

------------------------------------------------------------------------

# Phase 7 --- Documentation

Document:

-   `WorkflowStream`
-   `stream_workflow()`
-   event delivery
-   `stream.result`
-   `stream.error`
-   per-execution EventBus isolation
-   relationship between EventBus and WorkflowStream
-   difference between workflow-event streaming and token streaming

Example:

``` python
stream = stream_workflow(state)

for event in stream:
    print(event.type)

if stream.error:
    print(stream.error)

final_state = stream.result
```

------------------------------------------------------------------------

# Phase 8 --- Full Regression

Run the complete test suite.

The Sprint 13 changes must not break existing functionality.

Verify:

-   workflow execution
-   executor behavior
-   completion
-   replanning
-   persistence
-   resume
-   EventBus
-   audit listener
-   metrics listener
-   agent events
-   streaming

------------------------------------------------------------------------

# Out of Scope

Sprint 13 does **not** include:

-   LLM token streaming
-   modifying the Executor into a streaming executor
-   replacing EventBus
-   LangGraph `app.stream()` as the public streaming mechanism
-   FastAPI
-   SSE
-   WebSockets
-   HTTP chunked responses
-   second event systems

------------------------------------------------------------------------

# Final Architecture

``` text
                    LangGraph Workflow
                           │
                           ▼
                      app.invoke()
                           │
                           ▼
                       EventBus
                           │
                    WorkflowEvent
                           │
                           ▼
                   Queue[WorkflowEvent]
                           │
                           ▼
                    WorkflowStream
                           │
                           ▼
                        Caller
```

The workflow state remains authoritative for:

-   output
-   persistence
-   resume
-   completion state

The stream provides the runtime progress view.

------------------------------------------------------------------------

# Sprint 13 Completion Criteria

Sprint 13 is complete when:

-   `WorkflowStream` exists.
-   `stream_workflow()` exists.
-   EventBus remains unchanged.
-   Each stream has an independent EventBus.
-   Workflow execution occurs in a background thread.
-   WorkflowEvents are delivered in order.
-   Events are available before workflow completion.
-   Final state is available through `stream.result`.
-   Worker errors are exposed through `stream.error`.
-   Agent events are streamed.
-   Streaming executions are isolated.
-   Resume + streaming behavior is tested.
-   Existing resume semantics remain unchanged.
-   Documentation is updated.
-   Full regression passes.
-   Changes are committed and pushed.

------------------------------------------------------------------------

## Current Status

## Current Status

Sprint 13 implementation is complete.

- Phase 1 — WorkflowStream abstraction:
- Phase 2 — EventBus → Queue bridge:
- Phase 3 — Background workflow execution:
- Phase 4 — Result/error lifecycle:
- Phase 5 — Core streaming tests:
- Phase 6 — Resume + streaming:
- EventBus isolation between concurrent streams:
- Phase 7 — Documentation:
- Full regression: **231 tests passed**

Final implementation commit:
`12a14e16 Add runtime workflow event streaming`
