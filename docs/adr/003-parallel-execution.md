# ADR-003: Parallel Execution

## Status

Accepted

## Context

Independent workflow steps may be executed concurrently when their dependencies are satisfied.

Sequential execution would unnecessarily increase workflow execution time when multiple steps are ready at the same time.

## Decision

The Executor executes ready independent workflow steps in parallel using a thread pool.

The maximum number of concurrent workers is controlled by `max_parallel_workers` in `RuntimeConfig`.

Steps are eligible for execution only when their dependencies have been satisfied.

## Consequences

### Positive

- Independent workflow steps can execute concurrently.
- Workflow execution time can be reduced.
- Parallelism is configurable.

### Negative

- Concurrent execution introduces additional execution complexity.
- Execution history must correctly associate results with their individual step IDs.
- The configured worker limit bounds concurrency.

## Implementation

Parallel execution is implemented in the Executor.

Execution history records the results of individual steps independently.

Persistence preserves the execution state required to resume workflows correctly.
