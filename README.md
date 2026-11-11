# AgentBox

A standalone environment for creating, cloning, testing, evaluating, versioning and evolving AI agents.

## Current repository status

The initial content is a **research extraction** from the user's uploaded `chatgpt_22-26.zip`. It is not yet a working agent runtime.

- `research/legacy-extracts/` contains selected historical code examples.
- `research/README.md` describes the extraction and known limitations.
- `research/source-map.md` maps repository files and candidate concepts to their ZIP source documents.

## Working principles

1. Use the uploaded ZIP as the source basis for this extraction phase.
2. Do not use OpenAgents or ASPIRE as implementation sources.
3. Preserve provenance and distinguish source examples from new implementation.
4. Keep the first prototype small and independently testable.
5. Do not execute untrusted agent-generated code without a genuine isolation boundary.

## Next design target

Map the source concepts into a minimal AgentBox lifecycle:

`define → version → clone/mutate → test → evaluate → promote or rollback`

No production readiness or end-to-end runtime validation is claimed at this stage.
