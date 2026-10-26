# Sprint 19 — Dockerization and Reproducible Local Deployment

## Objective

Containerize the Orion FastAPI application for reproducible local deployment while keeping secrets and persistent ChromaDB data outside the image.

## Environment

- Python base image: `python:3.11-slim`
- Docker image: `orion:0.2`
- Container name: `orion-api`
- Published port: `8000`
- ChromaDB named volume: `orion_chroma`
- Volume mount: `/app/chroma_db`
- Branch: `main`
- Latest related commit: `00dc924`

## Work Completed

### 1. Docker configuration

- Added a root-level `Dockerfile`.
- Installed application dependencies from `requirements.txt`.
- Configured Uvicorn to listen on `0.0.0.0:8000`.
- Added `.dockerignore` to exclude secrets, Git metadata, virtual environments, caches, local ChromaDB data, and build artifacts.
- Built image `orion:0.2` successfully on the home laptop.

### 2. Runtime configuration and persistence

- Started container `orion-api` with port 8000 published.
- Supplied runtime configuration through `.env`.
- Mounted named volume `orion_chroma` at `/app/chroma_db`.
- Confirmed the volume mount through Docker configuration inspection.
- Replaced the exposed Google API key after it appeared in terminal output. Never print or commit secret values.

The volume mount is verified, but survival of actual ChromaDB data across container recreation has not been demonstrated.

### 3. API verification

- `GET /health` returned `status: ok`.
- `GET /llm-usage` returned HTTP 200 with empty usage totals immediately after startup.
- OpenAPI inspection confirmed the routes:
  - `GET /health`
  - `GET /llm-usage`
  - `POST /workflow`
  - `POST /workflow/stream`

### 4. Automated tests

- Full regression suite: 265 passed, 1 warning in the previously recorded run.
- Focused API and stream tests: 13 passed, 1 deprecation warning.
- The streaming API test uses mocked workflow execution. These tests do not establish successful live Gemini-backed SSE execution inside Docker.

### 5. Documentation and delivery

- Updated `README.md` with Docker build, run, verification, and volume instructions.
- Committed Docker configuration and Sprint 19 documentation.
- Pushed the README update in commit `00dc924`.
- Synchronized the office laptop with `origin/main`.

## Acceptance Criteria

- [x] Dockerfile builds the Orion image.
- [x] Docker configuration starts Uvicorn on port 8000.
- [x] `.dockerignore` excludes environment files, virtual environments, caches, and local ChromaDB data.
- [x] Container starts successfully on the home laptop.
- [x] `GET /health` succeeds from the running container.
- [x] `GET /llm-usage` responds without a live model request.
- [x] Runtime secrets are supplied outside the image.
- [x] README contains local Docker instructions.
- [x] Docker configuration and documentation are committed and pushed.
- [x] Focused API and streaming tests pass.
- [ ] Demonstrate that actual ChromaDB data survives container recreation.
- [ ] Verify live Gemini-backed SSE execution in Docker when provider quota permits.

## Known Limitations and Risks

- Most dependencies in `requirements.txt` are not pinned, so subsequent builds may resolve different versions.
- The container currently uses the base image's default user. Non-root execution should be considered before production deployment.
- Hugging Face model download and cache behavior may depend on network access and local cache state.
- Client disconnect cancellation and background-thread lifecycle limitations remain relevant to SSE workflow reliability.
- Authentication, TLS, production hosting, and cloud deployment are outside this sprint.

## Remaining Work

1. Verify ChromaDB data persistence across container recreation when safe test data is available.
2. Verify live SSE execution without exposing secrets, when provider quota permits.
3. Consider dependency pinning and non-root execution as separate hardening work.

## Conclusion

Sprint 19 delivered a working local Docker deployment, basic API health verification, runtime secret configuration, named-volume mounting, and updated documentation.

Local deployment is validated. End-to-end live SSE behavior and actual data survival across container recreation remain explicitly unverified.
