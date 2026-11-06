---
id: T8
title: "Write the three invariant SQL checks: unique document and line, unique entry id, unambiguous mapping"
layer: "domain"
deps: ["T1", "T6", "T7"]
blocks: ["T11"]
acs: ["AC-06", "AC-11"]
files_hint: ["products/unified_gl/invariants/", "tests/unit/test_invariants.py"]
owner: "maksym.shkilov@gmail.com"
estimate: "S"
context_budget: "M"
status: "todo"
step: ""
---

<!-- Self-contained task. Inlined chunks carry a provenance signature; the source always wins.
To the executing agent: work from what is inlined here. If a slice is insufficient, ambiguous, or contradicts the code in front of you, open the named file for the full text and follow that. Do not invent the missing part. -->

# T8 — Write the three invariant SQL checks: unique document and line, unique entry id, unambiguous mapping

## Place in the sequence

- **Blocked by:** T1 — Extend the runner with manifest keys, clean start, invariant phase and InvariantViolation, T6 — Create the control views (independent raw side of the completeness gate), T7 — Create staging.ledger_entry: the aligned entry set (neutral SQL) · **Blocks:** T11 — Activate unified_gl: product.toml manifest, smoke-test update, timed CI run · **Wave:** 4, needs the runner phase (T1), the control views (T6) and the entry table (T7).
- **Lane:** Own lane (new folder `products/unified_gl/invariants/`).

## Why (user story)

> **As an** Owner  
> **I want** the aligned entry set to have a documented, stable shape and identifiers that do not change between runs  
> **So that** the USD conversion step can build on it without rework
>
> — `spec.md §4, US-07, verbatim` · full text: [spec.md](../spec.md)

> **As a** Reviewer  
> **I want** to see every entry carry the group account its local account maps to, and see any entry whose local account has no mapping  
> **So that** no entry silently disappears or lands in a blank account
>
> — `spec.md §4, US-05, verbatim` · full text: [spec.md](../spec.md)

Delivers the business rules that stop the run: a repeated key and an ambiguous mapping.

## Inlined context

> **ADR-0003 (feature), decision:** Option 1. It keeps the check in neutral SQL that runs on both engines and names the offending business keys in the message. Engine constraints (`PRIMARY KEY`, `UNIQUE`) were set aside from the start: Delta tables on Databricks do not enforce them (ADR-0004 of the repository), and they cannot name source system, document and line as AC-06 requires. Option 2 makes the core import product code and moves the logic out of SQL.
>
> — `adr/0003-stop-the-run-on-sql-invariant-checks-declared-in-the-manifest.md, Decision outcome, verbatim` · full text: [adr/0003-stop-the-run-on-sql-invariant-checks-declared-in-the-manifest.md](../adr/0003-stop-the-run-on-sql-invariant-checks-declared-in-the-manifest.md)

> `(belegnummer, zeile)` unique per source system is enforced by the invariant check, not by the engine. … `(source_system, local_account)` occurs in exactly one row (AC-11, after `clarify`: a repeat with the same or another group account is an error), enforced by the invariant check.
>
> — `data-model.md §Entities, raw.erp_a_export / raw.account_mapping Constraints, abridged` · full text: [data-model.md](../data-model.md)

> | 2, repeated key | `invariant violation: unique document and line` | one line per offender: source system, document, line (AC-06) |
> | 2, repeated entry id | `invariant violation: unique entry id` | source system, document, line of each entry sharing the id (AC-06) |
> | 2, ambiguous mapping | `invariant violation: unambiguous mapping` | source system and local account (AC-11), whether the group accounts differ or repeat |
>
> — `cli.md §3.4 Standard error, verbatim` · full text: [cli.md](../contracts/cli.md)

> the check on the raw records of each export runs before any readability rule is applied, so an unreadable duplicate also stops the run (checked on the control views, which contain unreadable entries too)
>
> — `spec.md §5 AC-06 + data-model.md Indexes «Document and line uniqueness», abridged` · full text: [spec.md](../spec.md)

> Hard rule: invariant SQL is neutral SQL, one file per check, zero rows = fine; the file name (without number and extension) is the name the CLI prints after `invariant violation:`.
>
> — `adr/0003 Considered options 1 + cli.md §3.4, abridged (rule restated)` · full text: [adr/0003-stop-the-run-on-sql-invariant-checks-declared-in-the-manifest.md](../adr/0003-stop-the-run-on-sql-invariant-checks-declared-in-the-manifest.md)

> Product SQL is dialect-neutral (runs on DuckDB and Spark SQL); engine differences go into an adapter — repo ADR-0004.
>
> — `sad.md §2 Constraints, Technical, abridged` · full text: [sad.md](../sad.md)

**Fallback:** insufficient or contradicted by the code → read the named file in full ([spec.md](../spec.md) · [sad.md](../sad.md) · [data-model.md](../data-model.md) · [cli.md](../contracts/cli.md) · [adr/](../adr/)) and follow it. Do not guess.

## Data delta

No DB changes.

## API contract

Internal — no API surface.

## Acceptance criteria

### AC-06 (US-07) — domain invariant violation

> **Given** aligned entries from both source systems, including two entries of one document that share date, account and amount, and both exports carry an explicit document number and line number for every entry  
> **When** the Owner runs the product twice  
> **Then** every entry has an identifier derived from source system, document and line (the three values in this order, as written in the source apart from trimmed spaces, joined by a fixed separator; the line takes part as a whole number, so «01» and «1» give the same identifier, while the document is taken as written in the source with trimmed spaces only), the identifiers are unique across both source systems, each entry keeps the same identifier in both runs, and if two entries ever shared an identifier, or one export held the same document and line twice (checked on the raw records of each export before any readability rule is applied, so an unreadable duplicate also stops the run), the run would stop with an error that names the source system, document and line (an error, not a gate result)
>
> — `spec.md §5, AC-06, verbatim` · full text: [spec.md](../spec.md)

### AC-11 (US-05) — domain invariant violation

> **Given** the account mapping lists the same local account of the same source system more than once, either with two different group accounts or with the same group account repeated  
> **When** the product is run  
> **Then** the run stops with an error (not a gate result) that tells the Reviewer which source system and local account are ambiguous, because each local account of a source system has exactly one row in the account mapping
>
> — `spec.md §5, AC-11, verbatim` · full text: [spec.md](../spec.md)


## Checklist

- [ ] `01_unique_document_and_line.sql`: from `raw.control_erp_a` and `raw.control_erp_b` return `source_system, document, line` having `count(*) > 1` — `products/unified_gl/invariants/`
- [ ] `02_unique_entry_id.sql`: from `staging.ledger_entry` return the `source_system, source_document, source_line` of every entry that shares an `entry_id` — `products/unified_gl/invariants/`
- [ ] `03_unambiguous_mapping.sql`: from `raw.account_mapping` return `source_system, local_account, count(*)` having `count(*) > 1` (differing or identical group accounts) — `products/unified_gl/invariants/`
- [ ] Tests on tmp copies of the inputs (runner from T1 with a manifest listing the three files): clean data → zero rows; duplicate document+line (also an unreadable duplicate) → rows name source system, document, line; ambiguous mapping with two different group accounts and with a repeated identical row → rows name source system and local account — `tests/unit/test_invariants.py`
- [ ] Test identifiers are identical in two consecutive runs and unique across both sources (AC-06) — `tests/unit/test_invariants.py`

## Edge cases

| Case | Behaviour |
|---|---|
| Same document and line twice, one of them unreadable | caught: the check runs on control views before any readability rule |
| Two entries share an `entry_id` | rows name each entry's source system, document and line |
| Mapping row repeated with the same group account | still an error (AC-11) |
| Same account code in both source systems | NOT an error: uniqueness is per source system |
| Document `A-1` line `01` and line `1` | same integer line → duplicate key |

## Definition of Done

- [ ] Three invariant files exist and return zero rows on the clean committed data
- [ ] Tests for repeated key (incl. unreadable duplicate), repeated entry id, and ambiguous mapping (differing and identical) pass (AC-06, AC-11)
- [ ] Two runs give identical identifiers
- [ ] lint clean
- [ ] every Hard Rule inlined above still holds
- [ ] lint + vet clean
