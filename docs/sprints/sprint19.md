# Sprint 19 --- Dockerization

## Objective

Containerize the Orion FastAPI application so it can be built and run in
a reproducible Linux environment using Docker Desktop and the WSL 2
backend.

## Environment

-   Host OS: Windows 11 Pro
-   Container runtime: Docker Desktop with WSL 2
-   Docker version: 29.8.2
-   Python base image: `python:3.11-slim`
-   Project branch at start: `main`
-   Starting commit: `11d56d6` --- `Add SSE workflow streaming endpoint`

## Work completed

### 1. Docker development environment

-   Installed and verified WSL 2 with Ubuntu.
-   Installed Docker Desktop.
-   Confirmed that `docker info` returned Docker Server information and
    that the Docker engine was reachable.

### 2. Docker configuration

Added a root-level `Dockerfile`:

-   Uses `python:3.11-slim`.
-   Sets `/app` as the working directory.
-   Installs dependencies from `requirements.txt` inside the image.
-   Copies the Orion source into the image.
-   Exposes port `8000`.
-   Starts FastAPI with
    `uvicorn api.main:app --host 0.0.0.0 --port 8000`.

Added a root-level `.dockerignore` to exclude local secrets, Git
metadata, virtual environments, caches, local ChromaDB data, generated
workflow state, build artifacts, IDE files, and logs from the Docker
build context.

The existing `.gitignore` was inspected and left unchanged.

### 3. Image build

Built the image successfully with:

``` powershell
docker build -t orion:0.1 .
```

The build completed successfully, including dependency installation and
source copy. The image was tagged `orion:0.1`.

## API endpoints intended to be served

The existing FastAPI application in `api/main.py` defines:

-   `GET /health`
-   `POST /workflow`
-   `POST /workflow/stream` (Server-Sent Events)

The application code and endpoint definitions were not changed as part
of the initial Docker configuration.

## Validation status

  -----------------------------------------------------------------------
  Check                               Status
  ----------------------------------- -----------------------------------
  Docker Desktop engine reachable     Passed

  Docker image build                  Passed

  Container starts successfully       Not yet verified

  `GET /health` from the running      Not yet verified
  container

  `POST /workflow` from the running   Not yet verified
  container

  `POST /workflow/stream` from the    Not yet verified
  running container

  Runtime Google API key              Not yet verified
  configuration

  ChromaDB persistence using a Docker Not yet configured or verified
  volume
  -----------------------------------------------------------------------

## Next steps

1.  Start the container and inspect its status:

    ``` powershell
    docker run -d --name orion-api -p 8000:8000 orion:0.1
    docker ps -a
    ```

2.  If it exits or fails to start, inspect the logs:

    ``` powershell
    docker logs orion-api
    ```

3.  Test the health endpoint after confirming the container is running:

    ``` powershell
    Invoke-RestMethod http://localhost:8000/health
    ```

4.  Configure `GOOGLE_API_KEY` securely at runtime, without putting the
    key in the Dockerfile or committing it to Git.

5.  Decide and test how ChromaDB data will persist across container
    recreation. The local `chroma_db/` directory is excluded from the
    image build context.

6.  Test both workflow endpoints, including SSE streaming.

7.  Run the existing automated test suite in an appropriate environment.

8.  Review the dependency pinning strategy separately; most dependencies
    in `requirements.txt` are currently unpinned. Do not change versions
    without testing.

## Screenshots / evidence

Recommended evidence to capture as validation progresses:

1.  **Docker image build success** --- terminal showing
    `docker build -t orion:0.1 .` completed and the image was tagged.
2.  **Container running** --- Docker Desktop Containers view or
    `docker ps` showing `orion-api` running.
3.  **Health endpoint response** --- PowerShell or browser showing the
    response from `http://localhost:8000/health`.
4.  **SSE endpoint test** --- a successful request to `/workflow/stream`
    showing named workflow events, with secrets and sensitive output
    redacted.

The first item is available from the completed build. The remaining
screenshots should only be added after those checks pass.

## Notes and limitations

-   The Docker image build succeeded, but a successful image build does
    not prove that the application starts or that all endpoints work
    inside the container.
-   The Google API key has not yet been passed to the container.
-   Hugging Face embedding-model download/cache behavior has not yet
    been verified inside the container.
-   ChromaDB persistence has not yet been configured or verified.
-   No application source files were intentionally modified for this
    initial Docker setup.

## Completion criteria

Sprint 19 should be marked fully validated only after the container
starts, `/health` responds successfully, runtime secrets are supplied
safely, and the synchronous and SSE workflow endpoints have been tested.
ChromaDB persistence behavior should also be documented and tested.
