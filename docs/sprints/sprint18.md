# Sprint 18 — Server-Sent Events (SSE) for Workflow Streaming

## Objective

Expose the existing Orion workflow events through a streaming HTTP API while reusing the existing WorkflowStream and EventBus infrastructure.

## Scope

### 1. SSE API Endpoint
- Add `POST /workflow/stream`.
- Accept a validated workflow question using the existing WorkflowRequest schema.
- Return a Server-Sent Events response using `text/event-stream`.
- Preserve the existing `GET /health` and `POST /workflow` endpoints.

### 2. Workflow Integration
- Reuse the existing compiled LangGraph workflow through WorkflowStream.
- Allow WorkflowStream to accept an optional EventBus.
- Attach the stream queue and logging, metrics, and audit listeners to the same request-scoped EventBus.
- Initialize workflow state independently for each request.
- Preserve the existing CLI and workflow routing architecture.

### 3. Event Serialization and Errors
- Serialize WorkflowEvent fields as JSON.
- Use the existing WorkflowEventType values as SSE event names.
- Include timestamps, step and tool metadata, payloads, and agent metadata.
- Emit a generic SSE error event when workflow execution fails after streaming begins.
- Avoid exposing internal exception details in the API error event.

### 4. Testing
- Test SSE event delivery and serialization using mocked workflow execution.
- Test SSE error reporting.
- Run the full regression test suite.

## Acceptance Criteria

- [x] `POST /workflow/stream` returns an SSE response.
- [x] Workflow events are delivered using their existing event type names.
- [x] Event data is serialized as JSON.
- [x] The stream uses the same EventBus as request-scoped monitoring listeners.
- [x] Existing workflow-stream behavior remains compatible.
- [x] Workflow failures are reported through an SSE error event.
- [x] Existing REST API behavior is preserved by regression tests.
- [x] Full regression test suite passes.

## Testing Results

- Workflow-stream tests: **5 passed** after EventBus integration.
- API tests: verified successful REST requests, SSE event delivery, and SSE failure reporting.
- Full regression suite: **248 passed**.
- Hugging Face Hub authentication warning observed during local initialization; this was not a test failure.

## Known Limitations

- Workflow execution occurs in a background daemon thread.
- Client disconnection does not forcibly cancel an already-running workflow.
- Authentication, production deployment configuration, and Dockerization are out of scope.

## Deliverables

- `runtime/stream.py`
- `api/main.py`
- `tests/test_api.py`
- `docs/sprints/sprint18.md`