# Sprint 17 — FastAPI API Layer

## Objective

Expose the existing Orion LangGraph workflow through a REST API without modifying the existing CLI application or workflow architecture.

## Scope

### 1. API Setup
- Create `api/` package and `api/main.py`.
- Use FastAPI with Uvicorn.
- Keep the existing `app.py` CLI unchanged.

### 2. Endpoints

**Health Check — `GET /health`**
- Return API status.
- Confirm that the API is responsive.

**Execute Workflow — `POST /workflow`**
- Accept a user query through a validated request schema.
- Generate a unique `workflow_id` for each request.
- Initialize the workflow state with the required fields.
- Invoke the existing compiled LangGraph application from `workflow.graph`.
- Return the workflow ID and assistant response.

### 3. Workflow Integration
- Reuse the existing compiled graph; do not duplicate its nodes or routing logic.
- Initialize state independently for every request.
- Avoid sharing conversation history or request-specific event data across requests.
- Import the existing tool-registration module where required.
- Return a clean JSON response rather than serializing the entire internal workflow state.

### 4. Error Handling
- Validate incoming requests.
- Handle workflow execution failures gracefully.
- Return appropriate HTTP status codes without exposing internal exception details.

### 5. Testing
- Test the health endpoint.
- Test successful workflow requests using mocked workflow execution.
- Test invalid requests and workflow failures.
- Verify that separate requests receive independent workflow IDs and state.
- Run the existing regression test suite to ensure no CLI or workflow regressions.

## Acceptance Criteria

- [ ] FastAPI application starts successfully.
- [ ] `/health` returns a successful response.
- [ ] `/workflow` accepts a query and returns a JSON response.
- [ ] Existing LangGraph workflow is reused without duplication.
- [ ] Request state is isolated between API calls.
- [ ] Error handling and API tests are implemented.
- [ ] Existing tests continue to pass.
- [ ] Changes are committed only after verification.

## Out of Scope

- Server-Sent Events (SSE) and workflow streaming.
- Dockerization.
- Production deployment configuration and authentication.

These will be addressed in subsequent sprints.

## Deliverables

- `api/__init__.py`
- `api/main.py`
- `tests/test_api.py`
- `sprint17.md`
- Updated `requirements.txt` with compatible FastAPI and Uvicorn versions.
