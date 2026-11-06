---
id: T10
title: "Write the summary query and the exceptions report query"
layer: "app"
deps: ["T7"]
blocks: ["T11"]
acs: ["AC-01", "AC-02", "AC-14"]
files_hint: ["products/unified_gl/reports/summary.sql", "products/unified_gl/reports/exceptions_report.sql", "tests/unit/test_reports_sql.py"]
owner: "maksym.shkilov@gmail.com"
estimate: "S"
context_budget: "M"
status: "todo"
step: ""
---

<!-- Self-contained task. Inlined chunks carry a provenance signature; the source always wins.
To the executing agent: work from what is inlined here. If a slice is insufficient, ambiguous, or contradicts the code in front of you, open the named file for the full text and follow that. Do not invent the missing part. -->

# T10 — Write the summary query and the exceptions report query

## Place in the sequence

- **Blocked by:** T7 — Create staging.ledger_entry: the aligned entry set (neutral SQL) · **Blocks:** T11 — Activate unified_gl: product.toml manifest, smoke-test update, timed CI run · **Wave:** 4, needs only the entry table (T7); parallel to T8 and T9.
- **Lane:** Own lane (new folder `products/unified_gl/reports/`).

## Why (user story)

> **As a** Reviewer  
> **I want** to run one command and see how many entries each source system delivered in each transaction currency  
> **So that** I can tell at a glance that the data arrived
>
> — `spec.md §4, US-02, verbatim` · full text: [spec.md](../spec.md)

Delivers what the Reviewer reads first: entries and totals per source system and currency, plus the untranslated descriptions.

## Inlined context

> **ADR-0004 (feature), decision:** Option 1. What to show stays visible as SQL in the product; how to show it (table layout, CSV writing, build folder) exists once in the core and does not depend on the engine. Option 2 puts file writing into engine-specific code, so each engine needs its own export and the summary has no shared home. A per-product Python report module was ruled out at the start, because `CLAUDE.md` forbids copying shared behaviour into a product.
>
> — `adr/0004-let-products-declare-report-queries-that-the-core-renders.md, Decision outcome, verbatim` · full text: [adr/0004-let-products-declare-report-queries-that-the-core-renders.md](../adr/0004-let-products-declare-report-queries-that-the-core-renders.md)

> S->>D: runs the summary query on the aligned entry set. D-->>S: one row per source system and transaction currency with entry count, debit total and credit total. The currency list comes from the aligned entries and never from the rates file (AC-14). S->>D: runs the exceptions report query. D-->>S: one row per aligned entry whose description has no translation, with source system, document, line and original text (AC-02, written even when empty).
>
> — `sad.md §6, Flow 4, abridged` · full text: [sad.md](../sad.md)

> | Writes | `build/unified_gl/exceptions_report.csv` | Header `source_system,source_document,source_line,original_description`; **always** written, header only when no record (AC-02); also written after a failed gate (SAD §1 override) |
> **Summary table** … columns `source_system`, `transaction_currency`, `entries`, `debit_total`, `credit_total` (AC-01).
>
> — `cli.md §3.2 + §3.3 item 1, abridged` · full text: [cli.md](../contracts/cli.md)

> The `original_description` column exists because the report cannot tell «untranslated» from «translated» using `description` alone.
>
> — `data-model.md §Entities, staging.ledger_entry, original_description note, abridged` · full text: [data-model.md](../data-model.md)

> Note (this task's rule): «untranslated» is decided by the absence of a translation-list row for `(source_system, original_description)` with exact whole-text equality — no case-insensitive or word-level matching.
>
> — `spec.md §5, AC-02, abridged` · full text: [spec.md](../spec.md)

> Product SQL is dialect-neutral (runs on DuckDB and Spark SQL); engine differences go into an adapter — repo ADR-0004.
>
> — `sad.md §2 Constraints, Technical, abridged` · full text: [sad.md](../sad.md)

**Fallback:** insufficient or contradicted by the code → read the named file in full ([spec.md](../spec.md) · [sad.md](../sad.md) · [data-model.md](../data-model.md) · [cli.md](../contracts/cli.md) · [adr/](../adr/)) and follow it. Do not guess.

## Data delta

No DB changes.

## API contract

Internal — no API surface.

## Acceptance criteria

### AC-01 (US-02) — happy path

> **Given** the Reviewer has a fresh clone of the repository, has done the one-time setup, and the product's exports are present  
> **When** the Reviewer starts the single run command  
> **Then** the run finishes successfully and prints, for each source system and each transaction currency, the number of entries loaded and their debit total and credit total, and states that both gates of the product passed; the summary also shows one number, the count of records in the exceptions report, always shown (0 included) next to the report name
>
> — `spec.md §5, AC-01, verbatim` · full text: [spec.md](../spec.md)

### AC-02 (US-03) — happy path

> **Given** the entries of both exports are loaded  
> **When** the Reviewer looks at the aligned entries  
> **Then** every entry from either source system shows the same attributes under the same names, with its description in one common language (a fixed, committed translation list, no external service), a real calendar date, a numeric amount, and one signed amount in which a debit is positive and a credit is negative, regardless of how its source wrote dates, numbers, debits and credits; in ERP A a debit or credit cell is filled when it is not empty (a cell holding zero counts as filled), and exactly one of the two is filled, with a number greater than zero, and in ERP B a positive amount is a debit and a negative amount is a credit; a description that has no entry in the translation list keeps its original text, its entry stays among the aligned entries (it is not an AC-09 case), and the description is written to the exceptions report (`exceptions_report.csv`), one record per aligned entry whose description has no translation, with the columns `source_system`, `source_document`, `source_line` and `original_description` (the same names as in the aligned entries), written to the build area on every run (with only its header when there is no such entry); a description is translated only when its whole text equals an entry of the translation list exactly (no word-level or case-insensitive matching), and the common language is English; missing exchange rates and reconciliation differences are not part of this report (rates belong to step 3, differences are reported by the completeness gate, AC-08)
>
> — `spec.md §5, AC-02, verbatim` · full text: [spec.md](../spec.md)

### AC-14 (US-07) — cross-context

> **Given** the next step needs an exchange rate for every transaction currency that is present  
> **When** the Owner reads the product documentation of the aligned entries  
> **Then** it lists every attribute of an aligned entry with its meaning (at least the identifier, source system, document, line, date, signed amount, transaction currency, local account, group account, description in the common language and original description), and the run summary lists exactly the transaction currencies that occur in the entries
>
> — `spec.md §5, AC-14, verbatim` · full text: [spec.md](../spec.md)


## Checklist

- [ ] `summary.sql`: per `source_system, transaction_currency` → `entries`, `debit_total` (sum of positive `signed_amount`), `credit_total` (sum of negated negative), ordered by source system then currency — `products/unified_gl/reports/summary.sql`
- [ ] `exceptions_report.sql`: columns `source_system`, `source_document`, `source_line`, `original_description` for aligned entries with no row in `raw.description_translation` (left join on source system and exact original text, `IS NULL`), ordered by the same three keys — `products/unified_gl/reports/exceptions_report.sql`
- [ ] Tests on the generator data: summary currencies equal the currencies in `staging.ledger_entry`; debit total equals credit total per document-balanced source; exceptions query returns the deliberately untranslated ERP A descriptions and nothing for ERP B — `tests/unit/test_reports_sql.py`
- [ ] Test with a currency removed from a tmp rates file: summary still lists exactly the currencies of the entries — `tests/unit/test_reports_sql.py`

## Edge cases

| Case | Behaviour |
|---|---|
| No untranslated description | exceptions query returns zero rows (CSV has only its header, written by T2) |
| Currency present in rates but not in entries | not in the summary (AC-14) |
| Translation differs only in case | treated as untranslated |
| Untranslated description in a failed-gate run | report still produced |

## Definition of Done

- [ ] Summary query returns one row per source system and currency present, with exact decimals (AC-01, AC-14)
- [ ] Exceptions query returns exactly the entries whose description has no exact translation row (AC-02)
- [ ] Both files are neutral SQL
- [ ] lint clean
- [ ] every Hard Rule inlined above still holds
- [ ] lint + vet clean
