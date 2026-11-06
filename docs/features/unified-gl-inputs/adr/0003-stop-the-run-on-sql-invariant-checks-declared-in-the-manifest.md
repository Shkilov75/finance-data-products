---
status: Accepted
owner: "maksym.shkilov@gmail.com"
reviewers: []
updated_at: "2026-11-05"
feature_size: "M"
ticket: ""
---

# 0003 — Stop the run on SQL invariant checks declared in the product manifest

- **Status:** Accepted
- **Date:** 2026-11-05
- **Deciders:** Owner + Architect (design session)

## Context

Two rules of this feature must end the run with an error that names the offenders, not appear as a gate result: a source system, document and line that occurs twice or an entry identifier that occurs twice (AC-06), and a local account that the account mapping assigns to two different group accounts (AC-11). With such data the identifiers and totals that follow would be wrong, so the product must not go on. The current runner knows only layers and gates; a failed gate is a normal result and the run goes on (ADR-0003 of the repository).

## Decision drivers

- AC-06 and AC-11: an error naming source system, document and line, or source system and local account; not a gate result.
- Reuse of the repository convention «a SQL file returns violating rows, zero rows is fine» (`docs/architecture-map.md`).
- Portability: the check must run on both engines (ADR-0004).
- Shared behaviour belongs in `src/fdp_core/`, not in a product (`CLAUDE.md`).

## Considered options

1. **An `invariants` list in `product.toml`** — SQL files with the zero-row convention. `fdp_core` runs them after the layers are built and before the gates; any returned row raises a typed `InvariantViolation` (in `errors.py`) whose message lists the rows; the CLI prints it and exits with code 2 (a failed gate exits with 1).
2. **A Python validation hook in the product** — a file in the product folder that `fdp_core` imports and calls after the layers are built.

## Decision outcome

**Chosen:** Option 1. It keeps the check in neutral SQL that runs on both engines and names the offending business keys in the message. Engine constraints (`PRIMARY KEY`, `UNIQUE`) were set aside from the start: Delta tables on Databricks do not enforce them (ADR-0004 of the repository), and they cannot name source system, document and line as AC-06 requires. Option 2 makes the core import product code and moves the logic out of SQL.

## Consequences

**Positive**
- Any later product can declare its own invariants with no core change.
- A bad input is told apart from a failed gate by the exit code and by the message.

**Negative**
- A new concept in the vocabulary (invariant check versus gate) that the README must explain and `CONTEXT.md` should define.
- The manifest gets a new key and the runner a new phase, so `fdp_core` changes in this feature, not only a product.

**Neutral**
- Run order in the core becomes: layers, invariants, gates, reports.
- Because invariants run after the layers are built, a duplicate key can already be inside the staging table when the error is raised; the run stops before any gate or report.

## Links

- Spec: [[../spec.md]] AC-06, AC-11
- SAD: [[../sad.md]] §4, §5, §8
- Related ADR: [[0001-expose-typed-flat-views-from-per-engine-adapters]]; repo ADR `docs/adr/0003-rebuild-layered-duckdb-no-migration-tool.md`
