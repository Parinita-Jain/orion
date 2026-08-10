# ADR-007: Dynamic Replanning Architecture

## Status

Accepted

---

## Context

AI workflows frequently encounter recoverable failures such as network timeouts, temporary API unavailability, or transient infrastructure errors.

Restarting the entire workflow would unnecessarily repeat successful work and increase execution time.

Orion therefore requires a mechanism to continue execution while preserving successful results.

---

## Decision

Introduce a dedicated dynamic replanning workflow consisting of:

- `CompletionStatus`
- Completion Node
- Failure Classifier
- Replanner Node

The Completion Node evaluates workflow state after execution.

Recoverable failures trigger the Replanner.

The Replanner generates only the additional execution steps required to satisfy the original user request.

The workflow graph routes execution according to the returned `CompletionStatus`.

---

## Consequences

### Advantages

- Successful execution is preserved.
- Failed work is isolated.
- Workflow routing becomes state-driven.
- Replanning is separated from execution logic.
- The architecture is extensible for future workflow features.

### Trade-offs

The current implementation appends newly generated steps to the existing execution plan.

Recoverable failed steps remain part of the execution history.

Consequently, the Completion Node continues to detect recoverable failures after replanning.

---

## Future Work

Sprint 10 will introduce **step supersession**.

Recoverable failed steps will be marked as superseded once replacement steps have been generated.

This preserves execution history while allowing workflows to complete successfully after replanning.