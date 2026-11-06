---
status: Accepted
owner: "maksym.shkilov@gmail.com"
reviewers: []
updated_at: "2026-11-05"
feature_size: "M"
ticket: ""
---

# 0001 — Expose typed flat views from per-engine adapters

- **Status:** Accepted
- **Date:** 2026-11-05
- **Deciders:** Owner + Architect (design session)

## Context

Spec §6 requires that product SQL contains no engine-specific construct, except reading the nested-record export (ERP B) and parsing the locale date and number formats, which live in one adapter folder per engine (`adapters/duckdb/`, `adapters/databricks/`). The spec does not say where the boundary between the adapter and the neutral SQL runs. The Databricks adapter cannot be verified until roadmap step 6, so whatever the adapter has to provide should be as small and as portable as possible.

## Decision drivers

- Portability: 0 engine-specific constructs in `products/unified_gl/sql/` and `gates/` (spec §6, ADR-0004).
- No guessing: a date or amount that cannot be read in its source format must stay visibly unreadable (AC-09).
- The Databricks path is unverified until step 6; the less engine surface it needs, the cheaper a late fix is.
- Time budget of the whole repository (10+ hours): two adapters have to stay small.

## Considered options

1. **Typed flat views** — each adapter loads the raw files as they arrived, flattens the nested records and creates views with fixed names and column types (date as DATE, amounts as DECIMAL, an unreadable value as NULL). The neutral SQL starts from these views.
2. **Parse functions called from neutral SQL** — each adapter loads the raw files and defines functions with agreed names (for example `parse_date_a`); the neutral staging SQL calls them on text columns.

## Decision outcome

**Chosen:** Option 1. The contract between the adapter and the neutral SQL is a list of view names and column types, which both engines can create with plain view definitions; no user-defined SQL functions are needed on Databricks, whose support in Free Edition cannot be checked before step 6. The neutral SQL never sees a date or number string.

## Consequences

**Positive**
- The neutral SQL stays free of dates and numbers as text; the only coupling between engines is the view contract.
- The Databricks adapter needs only view definitions and file reading, no function support.
- A third engine would be a new folder with the same views.

**Negative**
- The parsing rules are not visible in the neutral SQL; a Reviewer has to open the adapter folder and the product README has to say where to look.
- Both adapters must keep the same view contract; a drift shows only when step 6 runs on Databricks.
- The independent control path of the completeness gate (see the ADR on it) needs its own views in each adapter, so some parsing is written twice per engine.

**Neutral**
- `product.toml` paths contain an `{engine}` placeholder that `fdp_core` replaces with the engine name; `Config` gains an `engine` value, default `duckdb`.

## Links

- Spec: [[../spec.md]] §6 (portability), AC-09
- SAD: [[../sad.md]] §4, §5
- Related ADR: [[0002-compute-completeness-controls-on-an-independent-path]]; repo ADR `docs/adr/0004-share-sql-across-local-and-databricks.md`
