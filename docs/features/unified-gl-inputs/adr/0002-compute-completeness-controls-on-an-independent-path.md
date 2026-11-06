---
status: Accepted
owner: "maksym.shkilov@gmail.com"
reviewers: []
updated_at: "2026-11-05"
feature_size: "M"
ticket: ""
---

# 0002 — Compute completeness controls on an independent path of SQL control views

- **Status:** Accepted
- **Date:** 2026-11-05
- **Deciders:** Owner + Architect (design session)

## Context

The completeness gate compares the raw data with the aligned entries: entry count, total debits and total credits per source system and transaction currency, and every entry matched by source system, document and line (AC-07, AC-08). AC-07 requires that the raw-side figures come from reading the raw files separately from the alignment, not from reusing its parsing. If both sides shared one parser, a parsing defect would change both sides in the same way and the gate would pass on wrong data (devil's-advocate vector V1 in spec §1).

## Decision drivers

- A defect in the alignment parsing must be able to turn the gate red (AC-07, AC-08, spec §6 accuracy target «0 differences»).
- Gate convention: one SQL file, zero returned rows means PASS (ADR-0003, `docs/architecture-map.md`).
- Portability to Databricks (ADR-0004), which cannot be verified until roadmap step 6.
- Time budget: the second parsing path must stay small (three fields per source).

## Considered options

1. **Independent SQL control views in each adapter** — besides the typed views that feed the alignment (ADR-0001), each adapter creates control views over the same raw tables (`raw.control_erp_a`, `raw.control_erp_b`) that read date, amount and local account by a separately written expression. `gates/01_completeness.sql` stays neutral SQL and compares the control views with `staging.ledger_entry`.
2. **A Python gate that reads the committed files itself** — a registered Python gate parses the CSV and the nested file with the standard library and `Decimal` and compares the result with `staging.ledger_entry`.

## Decision outcome

**Chosen:** Option 1. It keeps the completeness gate a plain SQL file that returns the violating rows, runs on both engines through the existing adapter mechanism, and still has a separate code path for the raw side. Option 2 gives stronger independence but works only where the raw files are on the local disk, so step 6 would need a rewrite or a file-access layer, and the gate would stop following the one-SQL-file convention.

## Consequences

**Positive**
- The gate stays a declarative, readable SQL file; a Reviewer sees both sides of the comparison in SQL.
- No new gate mechanism in `fdp_core`.
- The same gate file runs on Databricks once the adapter provides the control views.

**Negative**
- Date, amount and account parsing is written twice per engine (alignment views and control views).
- The independence is of code, not of knowledge: if the Owner misreads a source format, both parsers can be wrong in the same way. This is covered by a test that compares the aligned entries with the known values from the generator, not by the gate.

**Neutral**
- An unreadable entry counts in the raw entry count of the control view but adds nothing to its debit or credit total (AC-09).
- Control views live in the `raw` schema, next to the files they read.

## Links

- Spec: [[../spec.md]] AC-07, AC-08, AC-09, §6
- SAD: [[../sad.md]] §4, §5
- Related ADR: [[0001-expose-typed-flat-views-from-per-engine-adapters]]
