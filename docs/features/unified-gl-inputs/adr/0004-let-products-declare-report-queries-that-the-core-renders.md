---
status: Accepted
owner: "maksym.shkilov@gmail.com"
reviewers: []
updated_at: "2026-11-05"
feature_size: "M"
ticket: ""
---

# 0004 — Let products declare report queries that the core renders

- **Status:** Accepted
- **Date:** 2026-11-05
- **Deciders:** Owner + Architect (design session)

## Context

The run must print a summary (entries, debit total and credit total per source system and transaction currency, both gates passed, number of records in the exceptions report, the currencies present; AC-01, AC-14), write an exceptions report as `exceptions_report.csv` (AC-02), name the violating rows of a failed gate (AC-08) and list reserved products (AC-13). The current runner prints only «N violating rows» per gate and returns a list of gate results. Steps 3, 7 and 8 will need the same kind of output.

## Decision drivers

- Shared behaviour lives in `src/fdp_core/`, never copied into a product (`CLAUDE.md`).
- The run writes only to the build area and does not change committed inputs (AC-12, spec §6.1).
- Portability: no engine-specific file writing in product SQL (spec §6, ADR-0004 of the repository).
- The Reviewer reads the summary first, so its content must be easy to find and change.

## Considered options

1. **Products declare SQL, the core renders** — `product.toml` gets `summary` (one SQL query whose rows the core prints as a table) and `exports` (pairs of a SQL query and a file name). After the gates `fdp_core` runs them, prints the table, and writes each export with the Python `csv` module into `build/<product>/`. The core also prints the violating rows of a failed gate and the list of reserved products.
2. **Engine-native export in the adapter** — the adapter writes the CSV with the engine's own statement (for example DuckDB `COPY ... TO`) and the summary is printed by a product-specific script.

## Decision outcome

**Chosen:** Option 1. What to show stays visible as SQL in the product; how to show it (table layout, CSV writing, build folder) exists once in the core and does not depend on the engine. Option 2 puts file writing into engine-specific code, so each engine needs its own export and the summary has no shared home. A per-product Python report module was ruled out at the start, because `CLAUDE.md` forbids copying shared behaviour into a product.

## Consequences

**Positive**
- Later products add a summary by writing one SQL file and one manifest line.
- File writing is the same on any engine, and always lands in `build/`.

**Negative**
- The output format is limited to a table and CSV files; free-form sentences such as «both gates passed» come from the core's gate list, not from the product.
- The core and the manifest schema grow in this feature (new keys, new phase after the gates).

**Neutral**
- Run order in the core: layers, invariants (ADR-0003 of this feature), gates, summary and exports.
- The exceptions report is written even when a gate fails, so the Reviewer can open it after a failed run.

## Links

- Spec: [[../spec.md]] AC-01, AC-02, AC-08, AC-12, AC-13, AC-14
- SAD: [[../sad.md]] §4, §5, §8
- Related ADR: [[0003-stop-the-run-on-sql-invariant-checks-declared-in-the-manifest]]
