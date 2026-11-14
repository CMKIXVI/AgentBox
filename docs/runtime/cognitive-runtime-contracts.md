# AgentBox cognitive runtime contracts

**Status:** typed lifecycle contracts and a tenant-scoped append-only run journal are implemented. No cognition, planning, orchestration, capability invocation, evidence attestation, or memory consolidation runtime is claimed.

## Canonical lifecycle

`intent → context → cognition → capability → responsibility → execution → observation → verification → memory`

The order is explicit and versioned. A run may emit multiple events in the same stage, but a transition may not skip or move backwards within one run. Iterative reasoning is represented by multiple cognition events in the cognition stage; a future controller may define a new bounded cycle/run rather than silently rewinding lifecycle history.

## Event envelope

Schema: `schemas/cognitive-event-v1.schema.json`  
Validator: `backend/app/cognitive_contract.py`

Every event binds:
- Tenant, run and trace identities.
- A strictly positive sequence number and immutable event ID.
- A lifecycle stage and a stage-compatible event type.
- Actor kind and actor identity.
- Timestamp, optional causation/correlation references.
- Input, output and evidence references.
- An explicit evidence status.

The envelope carries references and bounded metadata, not executable code or authority. It does not replace the existing tenant principal, authorization policy, execution service, registry, enterprise context, experience store or audit authority.

## Hard invariants

- Verification success/failure and accepted memory require verified evidence references.
- Capability selection requires an explicit versioned capability reference.
- Authorization decisions require a reference to the authorization decision/audit record. This event does not itself authorize an action.
- Lifecycle transition validation rejects skipped or backward stage movement.
- Model proposals and observations remain untrusted until verified through an independent evidence path.
- No event or payload may grant permissions, select tenant authority, resolve secrets, execute code, or promote a candidate.

## Deliberately not implemented

- Durable event persistence or hash-chained event storage.
- Cognitive state store, goal decomposition, planner, reflection or memory consolidation.
- Capability invocation or orchestration.
- Event-to-existing-audit atomic transaction.
- Trusted evidence attestation and provenance verification.
- API routes and frontend surfaces.

These are later vertical slices. The next runtime step is a tenant-scoped cognitive run/state service that uses existing identity and authorization authorities and persists append-only events without creating a parallel tenant or agent registry.


## Tenant-scoped run journal

Implementation: `backend/app/cognitive_runtime.py`  
API: `POST /v1/cognitive-runs`, `GET /v1/cognitive-runs/{run_id}`, `GET /v1/cognitive-runs/{run_id}/events`, and `POST /v1/cognitive-runs/{run_id}/events`.

A run is bound server-side to an existing immutable agent version and its registry content hash. The caller supplies a goal reference, not tenant identity, actor identity, agent hash, or executable prompt. Tenant and actor are taken from the authenticated principal. Creation and event append require idempotency keys bound to the request and actor. Event sequence assignment and stage advancement occur in one SQLite transaction. Event rows are protected by database triggers against update and deletion. Reads are tenant-scoped; a run belonging to another tenant is indistinguishable from a missing run.

The SQLite implementation is single-instance only. The service is included in API shutdown and in-memory store lifecycle coverage. Run/event persistence is not yet coupled atomically to the authorization audit transaction, and the event hash is an integrity digest for the stored envelope rather than a signed or chained tamper-proof log.
