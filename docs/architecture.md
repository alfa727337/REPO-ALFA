# Architecture

REPO ALFA is organized as a fault-tolerant pipeline. Each stage is independently observable, checkpointed, and allowed to fail without terminating the whole scan.

## Core flow

1. Static capture
2. Dynamic browser capture
3. Recursive route discovery
4. Asset collection
5. Framework/technology fingerprinting
6. Endpoint discovery
7. Source map inspection when published
8. Security posture review
9. Graph generation
10. Structured reporting

## Recovery model

Each asynchronous module is executed through `RecoveryEngine`. Failures are recorded per attempt and retried with exponential backoff. A final module failure is converted into a `ModuleResult(status="failed")` rather than crashing the full run.

## Evidence model

Artifacts are written under a target-specific output directory. Raw data is preserved separately from derived reports so future analyzers can reprocess the evidence without rescanning the target.

## Extensibility

New analyzers should accept already-captured evidence whenever possible. This keeps collection separate from interpretation and allows analyzers to be tested offline.
