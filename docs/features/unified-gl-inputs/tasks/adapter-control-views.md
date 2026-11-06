---
id: T6
title: "Create the control views (independent raw side of the completeness gate)"
layer: "migration"
deps: ["T5"]
blocks: ["T8", "T9", "T11"]
acs: ["AC-07", "AC-09"]
files_hint: ["docs/features/unified-gl-inputs/migrations/03_create_control_views.up.sql", "docs/features/unified-gl-inputs/migrations/03_create_control_views.down.sql", "products/unified_gl/adapters/duckdb/", "tests/unit/test_control_views.py"]
owner: "maksym.shkilov@gmail.com"
estimate: "S"
context_budget: "M"
status: "todo"
step: ""
---

<!-- Self-contained task. Inlined chunks carry a provenance signature; the source always wins.
To the executing agent: work from what is inlined here. If a slice is insufficient, ambiguous, or contradicts the code in front of you, open the named file for the full text and follow that. Do not invent the missing part. -->

# T6 — Create the control views (independent raw side of the completeness gate)

## Place in the sequence

- **Blocked by:** T5 — Create the DuckDB adapter files: raw load of the five inputs and the typed views · **Blocks:** T8 — Write the three invariant SQL checks: unique document and line, unique entry id, unambiguous mapping, T9 — Write the completeness gate and the mapping gate, T11 — Activate unified_gl: product.toml manifest, smoke-test update, timed CI run · **Wave:** 3, needs the raw tables of T5.
- **Lane:** Migration layer — serialized after T5 (shares `adapters/duckdb/`).

## Why (user story)

> **As a** Reviewer  
> **I want** to see a gate that fails when an entry or an amount is lost between the raw files and the aligned entries  
> **So that** I can trust the alignment
>
> — `spec.md §4, US-06, verbatim` · full text: [spec.md](../spec.md)

Delivers the raw side of the gate: a separate parse that counts unreadable entries but adds nothing to the totals.

## Inlined context

> **ADR-0002 (feature), decision:** Option 1. It keeps the completeness gate a plain SQL file that returns the violating rows, runs on both engines through the existing adapter mechanism, and still has a separate code path for the raw side. Option 2 gives stronger independence but works only where the raw files are on the local disk, so step 6 would need a rewrite or a file-access layer, and the gate would stop following the one-SQL-file convention.
>
> — `adr/0002-compute-completeness-controls-on-an-independent-path.md, Decision outcome, verbatim` · full text: [adr/0002-compute-completeness-controls-on-an-independent-path.md](../adr/0002-compute-completeness-controls-on-an-independent-path.md)

> One row per **raw** entry, unreadable ones included. Parsing is written separately from the typed views (feature ADR-0002). … The gate derives the raw debit total as the sum of positive `signed_amount`, the raw credit total as the sum of the negated negative values, and compares each raw entry with its aligned entry by `(source_system, document, line)` for `entry_date`, `signed_amount` and `local_account`.
>
> — `data-model.md §Views, control views, abridged` · full text: [data-model.md](../data-model.md)

> Both parsers (alignment and control) misread a source format in the same way (ADR-0002) — mitigation: test comparing the aligned entries with the known values of the generator; one test per deliberate source difference.
>
> — `sad.md §11, risk 2, abridged` · full text: [sad.md](../sad.md)

> Hard rule: the control views must NOT reuse the typed views or their parsing; the independence is the point of ADR-0002.
>
> — `adr/0002, Decision outcome, abridged (rule restated)` · full text: [adr/0002-compute-completeness-controls-on-an-independent-path.md](../adr/0002-compute-completeness-controls-on-an-independent-path.md)

> Product SQL is dialect-neutral (runs on DuckDB and Spark SQL); engine differences go into an adapter — repo ADR-0004.
>
> — `sad.md §2 Constraints, Technical, abridged` · full text: [sad.md](../sad.md)

**Fallback:** insufficient or contradicted by the code → read the named file in full ([spec.md](../spec.md) · [sad.md](../sad.md) · [data-model.md](../data-model.md) · [cli.md](../contracts/cli.md) · [adr/](../adr/)) and follow it. Do not guess.

## Data delta

| Column | Type | Notes |
|---|---|---|
| `source_system`, `document`, `line`, `currency`, `local_account` | VARCHAR / INTEGER | as in the typed views |
| `entry_date` | DATE | NULL when unreadable |
| `signed_amount` | DECIMAL(18,2) | NULL when the entry is unreadable for any reason (date, key, currency, account, amount, both/neither side filled, negative or zero or over-precise amount), so an unreadable entry counts as an entry and adds nothing to the debit and credit totals (AC-09) |

— `data-model.md §Views, raw.control_erp_a / raw.control_erp_b, verbatim rows; staged pair `migrations/03_create_control_views.{up,down}.sql`` · full text: [data-model.md](../data-model.md)

## API contract

Internal — no API surface.

## Acceptance criteria

### AC-07 (US-06) — happy path

> **Given** clean data loaded from both exports  
> **When** the completeness gate runs  
> **Then** it passes because, for each source system and transaction currency, the number of entries and the total of debits and credits in the raw data equal those in the aligned entries, and every raw entry, matched by source system, document and line, has exactly one aligned entry with the same date, signed amount and local account; the raw-side counts and totals are obtained from the loaded raw records by a separate reading, written independently of the alignment and not reusing its parsing; a record lost while the files are loaded is caught by a separate test that compares the number of records in each file with the number loaded
>
> — `spec.md §5, AC-07, verbatim` · full text: [spec.md](../spec.md)

### AC-09 (US-03) — error

> **Given** an entry whose date or amount cannot be read in the format of its source, including an ERP A entry whose debit and credit are both filled, both empty or negative, any entry of either source whose amount is zero, and any entry whose amount has more decimal places than its currency allows (2 for EUR, GBP and USD)  
> **When** the entries are aligned  
> **Then** the system does not guess a value: the entry is not accepted as aligned, so the completeness gate reports it as lost in the way AC-08 describes: the unreadable entry counts in the raw entry count but adds nothing to the raw debit or credit total, so the difference shows as a missing entry; the independent raw-side reading of AC-07 applies each of the unreadable-entry rules listed here by itself, so that no part of an unreadable entry reaches the raw totals
>
> — `spec.md §5, AC-09, verbatim` · full text: [spec.md](../spec.md)


## Checklist

- [ ] Promote `03_create_control_views.up.sql` to `adapters/duckdb/03_create_control_views.sql` (`raw.control_erp_a`, `raw.control_erp_b`); confirm it reads only the `raw.erp_*` tables, never `raw.typed_*` — `products/unified_gl/adapters/duckdb/`
- [ ] Test: for clean data both views have one row per file entry and `signed_amount` is NOT NULL on all of them — `tests/unit/test_control_views.py`
- [ ] Test the AC-09 list one rule at a time on a tmp copy of the raw tables: bad date, ERP A both filled, both empty, negative, zero amount, 3 decimals → row exists, `signed_amount` NULL — `tests/unit/test_control_views.py`
- [ ] Test that control and typed views agree on the clean generator data (cross-check, not shared code) — `tests/unit/test_control_views.py`

## Edge cases

| Case | Behaviour |
|---|---|
| Unreadable entry | stays in the view as a row with `signed_amount` NULL: counts as an entry, adds nothing to totals |
| ERP A both debit and credit filled | `signed_amount` NULL |
| Zero amount in either source | `signed_amount` NULL |
| Empty document, line, currency or account | `signed_amount` NULL (treated as unreadable together with AC-09) |

## Definition of Done

- [ ] Both control views create on top of the T5 raw tables; staged pair applies and reverts cleanly
- [ ] Test per AC-09 rule passes, each rule applied by itself
- [ ] No reference to `raw.typed_*` in the control view SQL (grep in the test)
- [ ] lint clean
- [ ] every Hard Rule inlined above still holds
- [ ] lint + vet clean
