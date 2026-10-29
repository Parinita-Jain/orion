# Sprint 20 — Workflow Lifecycle and Stream Reliability

## Objective

Improve the reliability and resource lifecycle of Orion workflow execution and Server-Sent Events (SSE) streaming. Define predictable behavior for successful completion, workflow errors, client disconnection, and cancellation without changing the existing workflow architecture unnecessarily.

## Context

- Sprint 18 introduced `POST /workflow/stream` using SSE and the existing `WorkflowStream` and `EventBus`.
- `WorkflowStream` executes the compiled LangGraph workflow in a background daemon thread and transfers events through a queue.
- Workflow exceptions are captured by the stream and exposed through its `error` property.
- The SSE API emits a generic error event when the workflow fails.
- Sprint 19 delivered local Docker deployment and basic API health verification.
- Existing API and stream tests use mocked workflow execution; live Gemini-backed SSE behavior in Docker remains unverified.
- Client disconnection does not currently guarantee cancellation of an executing workflow.

## Scope

### 1. Workflow lifecycle

- Inspect how `WorkflowStream` starts, tracks, and finishes workflow execution.
- Define explicit lifecycle states or equivalent observable behavior for running, completed, and failed execution.
- Ensure exceptions and final results remain accessible after execution ends.
- Ensure completion signaling cannot be confused with a normal workflow event.
- Avoid unsafe attempts to forcefully terminate Python threads.

### 2. SSE terminal behavior

- Define the expected behavior for successful completion and workflow failure.
- Ensure terminal events are consistent, documented, and not emitted more than once.
- Preserve existing `WorkflowEventType` names and event payload compatibility unless a justified change is approved.
- Keep internal exception details out of client-facing error messages.
- Ensure the response generator exits cleanly after stream completion.

### 3. Client disconnects and cancellation

- Investigate how FastAPI/Starlette exposes client disconnection to a streaming response.
- Define whether disconnects trigger cooperative cancellation, detach the client while execution continues, or use another documented policy.
- If cancellation is implemented, make it cooperative and ensure workflow components can observe the cancellation signal.
- Avoid introducing cancellation behavior that leaves background threads or event listeners running indefinitely.
- Document any limitations that cannot safely be resolved within the current workflow architecture.

### 4. Resource cleanup and concurrency

- Review EventBus subscriptions and queue lifetime.
- Ensure completed or failed streams do not retain unnecessary listeners or resources.
- Test multiple independent streams to confirm that events are not delivered to the wrong request.
- Prevent unbounded resource growth caused by abandoned streams where feasible.
- Preserve request-scoped logging, metrics, and audit listeners.

### 5. Testing

- Test successful workflow completion and terminal-event behavior using mocked execution.
- Test workflow exceptions and generic SSE error reporting.
- Test client disconnect behavior using the supported test-client or ASGI mechanisms.
- Test concurrent streams for isolation.
- Test cleanup after both success and failure.
- Run the full regression suite.
- Do not require live Gemini calls for routine tests.

## Acceptance Criteria

- [ ] Workflow lifecycle behavior is documented and consistently represented.
- [ ] Successful streams terminate predictably.
- [ ] Failed workflows produce a generic client-facing error without exposing internal details.
- [ ] Terminal events are not duplicated.
- [ ] Client-disconnect behavior is explicitly defined and tested.
- [ ] If cancellation is implemented, it is cooperative and tested.
- [ ] EventBus listeners and stream resources are cleaned up appropriately.
- [ ] Concurrent streams remain isolated.
- [ ] Existing REST and SSE behavior remains compatible or any intentional change is documented.
- [ ] Focused lifecycle and streaming tests pass.
- [ ] Full regression suite passes.
- [ ] README or technical documentation is updated if externally observable behavior changes.

## Implementation Plan

1. Inspect `runtime/stream.py`, `runtime/event_bus.py`, `api/main.py`, workflow nodes, and existing stream tests.
2. Write down the lifecycle and disconnect behavior supported by the current architecture.
3. Add or refine tests for completion, errors, concurrency, and cleanup before changing implementation.
4. Implement the smallest safe lifecycle and cleanup changes.
5. Add cooperative cancellation only if the workflow architecture can support it without unsafe thread termination.
6. Run focused tests, then the full regression suite.
7. Review API compatibility and document any remaining limitations.
8. Commit and push the completed work after reviewing the diff.

## Known Risks and Constraints

- Python threads cannot be safely forcefully terminated.
- A disconnected HTTP client does not automatically imply that the underlying workflow can be stopped.
- LangGraph execution may include synchronous or blocking operations that do not promptly observe cancellation.
- Queue and listener cleanup must not discard events that are still required by an active stream.
- Provider quota limitations make live Gemini-backed tests unsuitable as mandatory regression checks.
- Durable execution, restart recovery, distributed workers, authentication, TLS, and production cloud deployment are outside this sprint unless explicitly approved.

## Out of Scope

- Replacing LangGraph or the existing EventBus architecture.
- Implementing durable workflow persistence or restart recovery.
- Introducing a distributed task queue.
- Production cloud deployment and authentication.
- Changing LLM provider selection or quota-aware fallback policy.

## Deliverables

- Workflow lifecycle and cancellation design notes.
- Updated stream implementation, if required by the investigation.
- Focused lifecycle, disconnect, error, cleanup, and concurrency tests.
- Updated technical documentation where behavior changes.
- Full regression test results.
- Reviewed and pushed code and sprint documentation.

## Implementation Notes

### Implemented

- Added `EventBus.unsubscribe()` to remove a specific listener safely without affecting other subscribers.
- Updated `WorkflowStream` to unsubscribe its event listener when workflow execution completes or fails.
- Added `WorkflowStream.close()` so consumers can stop receiving events without forcibly terminating the workflow thread.
- Updated the SSE response generator to call `stream.close()` in a `finally` block, including when the response generator is closed early.
- Added `WorkflowStreamingResponse` to close the underlying workflow stream when the ASGI response finishes or exits due to a client disconnect.
- Preserved generic client-facing workflow error reporting so internal exception details are not exposed.
- Added API tests for response-generator cleanup and client-disconnect cleanup.
- Retained tests for workflow errors, listener cleanup, and concurrent stream isolation.

### Disconnect Policy

The current policy is to **close the client-facing stream and detach its event listener when the SSE response terminates or the client disconnects**. This prevents the disconnected client from continuing to consume events through that listener.

Closing the stream does not terminate the underlying LangGraph execution thread. The workflow may continue running after the client disconnects. Cooperative cancellation is not implemented.

### Remaining Limitations

- Background workflow execution is not cancelled when a client disconnects.
- Cooperative workflow cancellation has not been implemented.
- Live Gemini-backed SSE behavior in Docker remains unverified.
- Production behavior across all ASGI server and disconnect scenarios has not been exhaustively verified.
- Not all Sprint 20 acceptance criteria are complete.

## Verification Results

- Focused API and workflow-stream tests: 17 passed after the final response-cleanup implementation.
- Full regression suite: 270 passed.
- `git diff --check`: passed with no reported whitespace errors.

## Status

Partially implemented. Workflow listener cleanup, SSE generator cleanup, response-level client-disconnect cleanup, generic workflow error reporting, and regression tests are in place. Client-facing disconnect cleanup is tested, but the underlying workflow is not cancelled. Cooperative cancellation and live Gemini-backed SSE verification remain outstanding.
