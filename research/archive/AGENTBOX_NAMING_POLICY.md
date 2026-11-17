# AgentBox Naming and Normalisation Policy

**Status:** Mandatory for all code imported into AgentBox.

## 1. One product identity

AgentBox is the sole product identity and code namespace for recovered capabilities. Historical project names are source provenance, not names to carry into the AgentBox product.

A source family may have been developed under any earlier project name. Once selected for import, its implementation must be integrated as an AgentBox capability and must not retain the old product identity in shipped code.

## 2. What must be normalized

Unless an approved external contract requires an exact literal, normalize all code-facing identifiers:

- Repository directories, package names, Python modules, Rust crates, TypeScript packages and namespaces.
- Classes, functions, methods, public types, interfaces, enums and constants.
- API routes, schema identifiers, manifest fields and capability identifiers.
- CLI commands, service names, worker names, queue/topic names and workflow identifiers.
- Configuration keys, environment-variable prefixes, deployment resources and container labels.
- UI names, product labels, docs, examples, comments, test names and fixture identifiers.
- Build metadata, package metadata, telemetry service names and log namespaces.

Use the established AgentBox naming conventions and subsystem boundaries. Do not create a second product, runtime, registry, identity system or competing authority merely to preserve an old implementation's packaging.

## 3. What may retain historical names

Historical names may remain only where needed to preserve traceability or legal obligations:

1. Recovery catalogue and source-provenance metadata.
2. Migration records that map source identifiers to AgentBox identifiers.
3. Copyright, attribution and licence notices required by the applicable licence.
4. An exact third-party protocol, file format or external integration literal that cannot safely be renamed.

Any exception in item 4 must be isolated at the integration boundary, documented, tested, and must not become a public AgentBox product or namespace identity.

## 4. Required migration map

Every imported artifact must have a mapping record with at least:

| Field | Purpose |
|---|---|
| Source document and block | Exact historical origin |
| Original archive path and SHA-256 | Immutable provenance |
| Original package/module/symbol | Historical identifier |
| AgentBox package/module/symbol | New canonical identifier |
| External-literal exceptions | Exact names that cannot be changed and why |
| Licence and attribution obligations | Legal reuse conditions |
| Tests proving migration | Import, API, serialization and compatibility evidence |

The source identifier is retained in this migration record, not copied into the imported runtime as a legacy alias.

## 5. No legacy compatibility layer by default

Do not retain old package imports, class aliases, deprecated names, dual configuration keys, dual CLI commands, old branding, or wrapper packages simply to ease migration. They create parallel identities and long-term maintenance burden.

If an external consumer genuinely requires backward compatibility, approve it as a time-bounded adapter at the boundary. It must translate into canonical AgentBox types immediately, have an owner and removal condition, and must not leak into internal code.

## 6. Acceptance gate

Before merging an imported capability:

- Search the changed tree for the source product name and known aliases.
- Review every remaining occurrence and classify it as provenance-only, legally required, external protocol, or accidental leakage.
- Fail review if old names appear in internal package paths, public symbols, runtime logs, user-facing labels, configuration namespaces or new tests.
- Run import/build/type/lint/test suites after renaming.
- Test serialized manifests and persisted data migrations; renaming identifiers without a migration plan can corrupt existing installations.
- Verify licence compatibility independently. Naming normalization does not grant reuse rights or remove attribution obligations.
- Keep source hashes and provenance records unchanged.

## 7. Non-negotiable principle

**Preserve history in provenance; ship only AgentBox identity in code.**

Do not bulk-rename unreviewed archive contents. Normalize only after an artifact has passed provenance, completeness, dependency, licence, security and architecture review.
