---
id: T7
title: "Create staging.ledger_entry: the aligned entry set (neutral SQL)"
layer: "migration"
deps: ["T5"]
blocks: ["T8", "T9", "T10", "T11", "T12"]
acs: ["AC-02", "AC-04", "AC-09", "AC-10"]
files_hint: ["docs/features/unified-gl-inputs/migrations/04_create_staging_ledger_entry.up.sql", "docs/features/unified-gl-inputs/migrations/04_create_staging_ledger_entry.down.sql", "products/unified_gl/sql/staging/", "tests/unit/test_ledger_entry.py"]
owner: "maksym.shkilov@gmail.com"
estimate: "M"
context_budget: "M"
status: "todo"
step: ""
---

<!-- Self-contained task. Inlined chunks carry a provenance signature; the source always wins.
To the executing agent: work from what is inlined here. If a slice is insufficient, ambiguous, or contradicts the code in front of you, open the named file for the full text and follow that. Do not invent the missing part. -->

# T7 — Create staging.ledger_entry: the aligned entry set (neutral SQL)

## Place in the sequence

- **Blocked by:** T5 — Create the DuckDB adapter files: raw load of the five inputs and the typed views · **Blocks:** T8 — Write the three invariant SQL checks: unique document and line, unique entry id, unambiguous mapping, T9 — Write the completeness gate and the mapping gate, T10 — Write the summary query and the exceptions report query, T11 — Activate unified_gl: product.toml manifest, smoke-test update, timed CI run, T12 — Document the aligned entry attributes and the synthetic-data notice in the product README · **Wave:** 3, needs the typed views of T5.
- **Lane:** Migration layer — serialized after T6 in the migration sequence (T5 → T6 → T7); no file overlap with T6, so the order is only the migration rule.

## Why (user story)

> **As a** Reviewer  
> **I want** to see the entries of both exports in one common shape (same names, dates, numbers and one amount convention)  
> **So that** I can compare them without knowing either ERP
>
> — `spec.md §4, US-03, verbatim` · full text: [spec.md](../spec.md)

> **As a** Reviewer  
> **I want** to see every entry carry the group account its local account maps to, and see any entry whose local account has no mapping  
> **So that** no entry silently disappears or lands in a blank account
>
> — `spec.md §4, US-05, verbatim` · full text: [spec.md](../spec.md)

Delivers the aligned entry set itself: one shape, one amount convention, group account, common description, deterministic id.

## Inlined context

> The neutral SQL builds `staging.ledger_entry`: one row per accepted entry of either source system … Rules of the aligned set: an entry that cannot be read (AC-09) is not in the set; an entry with no mapping stays with an empty group account (AC-10); an entry whose description has no translation keeps the original text; amounts are fixed-precision decimals with 2 decimal places, never rounded.
>
> — `sad.md §5 Data flow + Rules of the aligned set, abridged` · full text: [sad.md](../sad.md)

> Acceptance rule (in neutral SQL, `04_create_staging_ledger_entry`): `entry_date` is not NULL, the signed amount is not NULL and not 0 (ERP A: exactly one of `debit_filled`/`credit_filled` is true, `debit` positive or `-credit`), document, line, currency and local account are present.
>
> — `data-model.md §Views, Acceptance rule, verbatim` · full text: [data-model.md](../data-model.md)

> `entry_id` = md5 hash of source system, document and line joined with a fixed separator; deterministic, available in DuckDB and Spark SQL; collisions are caught by the invariant check `unique entry id`.
>
> — `sad.md §8, ID strategy, abridged` · full text: [sad.md](../sad.md)

> No `PRIMARY KEY`/`UNIQUE` in DDL: on a repeated key DuckDB would raise a constraint exception before the invariant check can raise the typed `InvariantViolation`. … No `DEFAULT`, `CHECK`, trigger, audit column or soft delete.
>
> — `data-model.md §Entities, staging.ledger_entry Constraints, abridged` · full text: [data-model.md](../data-model.md)

> Product SQL is dialect-neutral (runs on DuckDB and Spark SQL); engine differences go into an adapter — repo ADR-0004.
>
> — `sad.md §2 Constraints, Technical, abridged` · full text: [sad.md](../sad.md)

> Shared behaviour lives in `src/fdp_core/`, never copied into a product. Products never import each other. IDs are deterministic hashes of business keys, never random UUIDs.
>
> — `CLAUDE.md §Conventions, abridged` · full text: [../../../CLAUDE.md](../../../../CLAUDE.md)

**Fallback:** insufficient or contradicted by the code → read the named file in full ([spec.md](../spec.md) · [sad.md](../sad.md) · [data-model.md](../data-model.md) · [cli.md](../contracts/cli.md) · [adr/](../adr/)) and follow it. Do not guess.

## Data delta

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `entry_id` | VARCHAR | NOT NULL, unique (invariant) | `md5(source_system \|\| '\|' \|\| source_document \|\| '\|' \|\| source_line)`, 32 hex characters, deterministic (AC-06); `source_line` is hashed as an integer, so «01» and «1» give the same identifier, the document as written in the source with trimmed spaces |
| `source_system` | VARCHAR | NOT NULL | `ERP_A` or `ERP_B` (US-04) |
| `source_document` | VARCHAR | NOT NULL | original document number (US-04) |
| `source_line` | INTEGER | NOT NULL | original line number (US-04) |
| `entry_date` | DATE | NOT NULL | real calendar date (AC-02) |
| `signed_amount` | DECIMAL(18,2) | NOT NULL, ≠ 0 | debit positive, credit negative; scale 2, never rounded (spec §6) |
| `transaction_currency` | VARCHAR | NOT NULL | EUR, GBP or USD in the data; the run summary lists the currencies found here (AC-14) |
| `local_account` | VARCHAR | NOT NULL | account in the source's own chart |
| `group_account` | VARCHAR | NULL allowed | NULL = no mapping row; the mapping gate fails on it (AC-10) |
| `description` | VARCHAR | NOT NULL | common language; the original text when no translation exists (AC-02) |
| `original_description` | VARCHAR | NOT NULL | the source's text; needed by the exceptions report, which cannot tell «untranslated» from «translated» using `description` alone |

— `data-model.md §Entities, staging.ledger_entry, verbatim; staged pair `migrations/04_create_staging_ledger_entry.{up,down}.sql`` · full text: [data-model.md](../data-model.md)

## API contract

Internal — no API surface.

## Acceptance criteria

### AC-02 (US-03) — happy path

> **Given** the entries of both exports are loaded  
> **When** the Reviewer looks at the aligned entries  
> **Then** every entry from either source system shows the same attributes under the same names, with its description in one common language (a fixed, committed translation list, no external service), a real calendar date, a numeric amount, and one signed amount in which a debit is positive and a credit is negative, regardless of how its source wrote dates, numbers, debits and credits; in ERP A a debit or credit cell is filled when it is not empty (a cell holding zero counts as filled), and exactly one of the two is filled, with a number greater than zero, and in ERP B a positive amount is a debit and a negative amount is a credit; a description that has no entry in the translation list keeps its original text, its entry stays among the aligned entries (it is not an AC-09 case), and the description is written to the exceptions report (`exceptions_report.csv`), one record per aligned entry whose description has no translation, with the columns `source_system`, `source_document`, `source_line` and `original_description` (the same names as in the aligned entries), written to the build area on every run (with only its header when there is no such entry); a description is translated only when its whole text equals an entry of the translation list exactly (no word-level or case-insensitive matching), and the common language is English; missing exchange rates and reconciliation differences are not part of this report (rates belong to step 3, differences are reported by the completeness gate, AC-08)
>
> — `spec.md §5, AC-02, verbatim` · full text: [spec.md](../spec.md)

### AC-04 (US-05) — happy path

> **Given** a local account that appears in the account mapping for its source system  
> **When** an entry that uses it is aligned  
> **Then** the entry carries the group account assigned to that local account for that source system, and the same local account code in the other source system can map to a different group account without affecting it
>
> — `spec.md §5, AC-04, verbatim` · full text: [spec.md](../spec.md)

### AC-09 (US-03) — error

> **Given** an entry whose date or amount cannot be read in the format of its source, including an ERP A entry whose debit and credit are both filled, both empty or negative, any entry of either source whose amount is zero, and any entry whose amount has more decimal places than its currency allows (2 for EUR, GBP and USD)  
> **When** the entries are aligned  
> **Then** the system does not guess a value: the entry is not accepted as aligned, so the completeness gate reports it as lost in the way AC-08 describes: the unreadable entry counts in the raw entry count but adds nothing to the raw debit or credit total, so the difference shows as a missing entry; the independent raw-side reading of AC-07 applies each of the unreadable-entry rules listed here by itself, so that no part of an unreadable entry reaches the raw totals
>
> — `spec.md §5, AC-09, verbatim` · full text: [spec.md](../spec.md)

### AC-10 (US-05) — error

> **Given** an entry whose local account has no row in the account mapping for its source system  
> **When** the entries are aligned  
> **Then** the entry stays among the aligned entries with an empty group account, and the mapping gate fails and names the source system and the local account
>
> — `spec.md §5, AC-10, verbatim` · full text: [spec.md](../spec.md)


## Checklist

- [ ] Promote `04_create_staging_ledger_entry.up.sql` to `products/unified_gl/sql/staging/04_create_staging_ledger_entry.sql`; check it has no DuckDB-only construct (no file reading, no engine functions beyond `md5`, `CAST`, `COALESCE`) — `products/unified_gl/sql/staging/`
- [ ] Test on the generator data (adapters loaded first): row count equals the number of readable raw entries; `signed_amount` sign (debit positive, credit negative) for both sources; same column names for both sources — `tests/unit/test_ledger_entry.py`
- [ ] Test `staging.ledger_entry` against the expected-entry list from `generate()`: `entry_id`, `signed_amount`, `group_account`, `description` equal for every entry — `tests/unit/test_ledger_entry.py`
- [ ] Test AC-04: a local account code present in both charts gets different group accounts per source system — `tests/unit/test_ledger_entry.py`
- [ ] Test AC-10 and AC-02 branches on a tmp copy: account without a mapping row → entry stays, `group_account` NULL; description without translation → entry stays, original text kept — `tests/unit/test_ledger_entry.py`
- [ ] Test AC-09 branch: unreadable entry is absent from the table — `tests/unit/test_ledger_entry.py`

## Edge cases

| Case | Behaviour |
|---|---|
| Local account missing in the mapping | entry stays with `group_account` NULL (mapping gate fails later, T9) |
| Description not in the translation list | `description` = original text; entry stays aligned (not an AC-09 case) |
| Description equal to a list entry except case or a word | no match: translated only on exact whole-text equality |
| Line `01` vs `1` | same integer line, same `entry_id` |
| Same account code in both sources | joined by source system AND local account, never by account alone |
| Unreadable entry | not inserted |

## Definition of Done

- [ ] Staged pair applies on DuckDB and its `.down.sql` reverts cleanly; the live file contains only neutral SQL
- [ ] Comparison with the generator's expected entries is equal for all rows (AC-02, AC-04)
- [ ] AC-09 and AC-10 branch tests pass
- [ ] lint clean
- [ ] every Hard Rule inlined above still holds
- [ ] lint + vet clean
