---
status: Accepted
owner: "maksym.shkilov@gmail.com"
reviewers: []
updated_at: "2026-11-04"
feature_size: "n/a (repo foundation)"
ticket: ""
---

# 0003 — Rebuild a DuckDB file from raw/staging/mart SQL layers, with no migration tool

- **Status:** Accepted
- **Date:** 2026-11-04
- **Deciders:** Owner + Architect (survey session)

## Context

Data is synthetic and fully reproducible from committed generators and CSVs; there is no long-lived production database to evolve (idea-brief §5). A persistence approach and an ID strategy are still needed, and gates must run before results are published.

## Decision drivers

- Deterministic, reproducible runs a reader can verify.
- Gates must be able to block publishing of the `mart` layer.
- Minimal tooling for a one-week demo.

## Considered options

1. **DuckDB file, rebuilt each run, layers `raw` -> `staging` -> `mart`, no migration tool** — schema is the layer DDL/SQL; IDs are deterministic hashes of business keys.
2. **DuckDB file plus incremental versioned migrations (up/down SQL)** — production-like schema evolution.
3. **Parquet/Delta files without a database** — lakehouse style, files per step.

## Decision outcome

**Chosen:** Option 1. A rebuild from scratch is deterministic and easy to show; layers give the gates a place to run between `staging` and `mart`. Deterministic hash keys make reruns byte-identical and tests stable.

## Consequences

**Positive**
- No migration state to manage; `migration_tool` is intentionally empty.
- Gate failure stops before `mart` is published, so a bad run never leaves a believable-looking result.

**Negative**
- Does not demonstrate schema-evolution practice; the README should say this is deliberate for a demo.
- Not suitable for incremental loads if the scope ever grows.

**Neutral**
- Adding a migration tool later is possible if a product needs persistent state.

## Links

- Brief: [[../idea-brief.md]] §5
- Map: [[../architecture-map.md]] Conventions, Datastores
- Related ADR: [[0001-use-python-duckdb-with-sql-files]]
