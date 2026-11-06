---
id: T5
title: "Create the DuckDB adapter files: raw load of the five inputs and the typed views"
layer: "migration"
deps: ["T3"]
blocks: ["T6", "T7", "T11"]
acs: ["AC-02", "AC-03"]
files_hint: ["docs/features/unified-gl-inputs/migrations/01_create_raw_inputs.up.sql", "docs/features/unified-gl-inputs/migrations/01_create_raw_inputs.down.sql", "docs/features/unified-gl-inputs/migrations/02_create_typed_views.up.sql", "docs/features/unified-gl-inputs/migrations/02_create_typed_views.down.sql", "products/unified_gl/adapters/duckdb/", "tests/unit/test_adapter_duckdb.py"]
owner: "maksym.shkilov@gmail.com"
estimate: "M"
context_budget: "M"
status: "todo"
step: ""
---

<!-- Self-contained task. Inlined chunks carry a provenance signature; the source always wins.
To the executing agent: work from what is inlined here. If a slice is insufficient, ambiguous, or contradicts the code in front of you, open the named file for the full text and follow that. Do not invent the missing part. -->

# T5 — Create the DuckDB adapter files: raw load of the five inputs and the typed views

## Place in the sequence

- **Blocked by:** T3 — Write the seeded data generator and commit the five synthetic input files · **Blocks:** T6 — Create the control views (independent raw side of the completeness gate), T7 — Create staging.ledger_entry: the aligned entry set (neutral SQL), T11 — Activate unified_gl: product.toml manifest, smoke-test update, timed CI run · **Wave:** 2, needs the committed input files (T3).
- **Lane:** Migration layer — serialized in the migration sequence T5 → T6 → T7.

## Why (user story)

> **As a** Reviewer  
> **I want** to see the entries of both exports in one common shape (same names, dates, numbers and one amount convention)  
> **So that** I can compare them without knowing either ERP
>
> — `spec.md §4, US-03, verbatim` · full text: [spec.md](../spec.md)

> **As a** Reviewer  
> **I want** to see for every aligned entry the source system, original document and original line it came from  
> **So that** I can check the alignment against the raw file
>
> — `spec.md §4, US-04, verbatim` · full text: [spec.md](../spec.md)

Delivers the raw copy as it arrived (traceability) and the typed flat views the neutral SQL starts from.

## Inlined context

> **ADR-0001 (feature), decision:** Option 1. The contract between the adapter and the neutral SQL is a list of view names and column types, which both engines can create with plain view definitions; no user-defined SQL functions are needed on Databricks, whose support in Free Edition cannot be checked before step 6. The neutral SQL never sees a date or number string.
>
> — `adr/0001-expose-typed-flat-views-from-per-engine-adapters.md, Decision outcome, verbatim` · full text: [adr/0001-expose-typed-flat-views-from-per-engine-adapters.md](../adr/0001-expose-typed-flat-views-from-per-engine-adapters.md)

> **ADR-0005 (feature), decision:** Option 1. A pretty-printed document with its lines nested under it is the form a Reviewer reads most easily and the closest to «nested records». DuckDB reads it with `read_json`; Spark needs the `multiLine` option, which is one setting in the Databricks adapter. Option 2 reads on Spark without options and diffs better in git, but a full document on one line is hard to read by eye.
>
> — `adr/0005-store-the-nested-erp-export-as-a-json-array-of-documents.md, Decision outcome, verbatim` · full text: [adr/0005-store-the-nested-erp-export-as-a-json-array-of-documents.md](../adr/0005-store-the-nested-erp-export-as-a-json-array-of-documents.md)

> `raw` is kept as it arrived: ERP A as text columns, ERP B still nested; the rates are loaded but not read in this step. The neutral SQL never sees a date or number string. A date or amount that cannot be read in its source format becomes empty (NULL) and is never guessed.
>
> — `sad.md §5 Data flow + §6 Flow 5 step 4, abridged` · full text: [sad.md](../sad.md)

> Staged DDL pairs `01_create_raw_inputs` (the five `raw.*` input tables) and `02_create_typed_views` (`raw.typed_erp_a`, `raw.typed_erp_b`) go to `products/unified_gl/adapters/duckdb/` (engine specific: file readers). Paths inside them are relative to the repository root, where `fdp run` is started.
>
> — `data-model.md §Staged DDL + migrations/01 header, abridged` · full text: [data-model.md](../data-model.md)

> Product SQL is dialect-neutral (runs on DuckDB and Spark SQL); engine differences go into an adapter — repo ADR-0004.
>
> — `sad.md §2 Constraints, Technical, abridged` · full text: [sad.md](../sad.md)

> **Hard rule:** the SQL files outside `adapters/` contain no file-reading code; engine-specific constructs (reading the nested export, locale date and number parsing) live only in `adapters/<engine>/`.
>
> — `spec.md §6, NFR «Portability of product SQL», abridged` · full text: [spec.md](../spec.md)

**Fallback:** insufficient or contradicted by the code → read the named file in full ([spec.md](../spec.md) · [sad.md](../sad.md) · [data-model.md](../data-model.md) · [cli.md](../contracts/cli.md) · [adr/](../adr/)) and follow it. Do not guess.

## Data delta

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `belegnummer` | VARCHAR | — | document number (explicit, AC-05) |
| `zeile` | VARCHAR | — | line number within the document (explicit, AC-05) |
| `buchungsdatum` | VARCHAR | — | posting date, text `DD.MM.YYYY` |
| `konto` | VARCHAR | — | local account (ERP A chart, 4 digits) |
| `sollbetrag` | VARCHAR | — | debit, text; empty when the entry is a credit |
| `habenbetrag` | VARCHAR | — | credit, text; empty when the entry is a debit |
| `waehrung` | VARCHAR | — | transaction currency (EUR, GBP, USD) |
| `buchungstext` | VARCHAR | — | description in German |

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `doc_id` | VARCHAR | — | document number |
| `posting_date` | VARCHAR | — | text `MM/DD/YYYY`, one per document |
| `currency` | VARCHAR | — | one transaction currency per document (AC-05) |
| `lines` | ARRAY of STRUCT(`line_no` VARCHAR, `account` VARCHAR, `amount` VARCHAR, `memo` VARCHAR) | — | nested lines; `amount` is signed text, `memo` is the description in English |

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `source_system` | VARCHAR | — | `ERP_A` or `ERP_B` |
| `local_account` | VARCHAR | — | account code in that source system's chart; the same code can occur in both systems with different group accounts (AC-04) |
| `group_account` | VARCHAR | — | account of the common chart |

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `source_system` | VARCHAR | — | `ERP_A` or `ERP_B` |
| `original_description` | VARCHAR | — | description exactly as the source wrote it |
| `common_description` | VARCHAR | — | the same text in the common language (English) |

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `date` | VARCHAR | — | ISO `YYYY-MM-DD`, one row per currency (USD included, rate 1) per calendar day, 2026-01-01 to 2026-03-31 |
| `currency` | VARCHAR | — | EUR, GBP, USD (USD rate is 1) |
| `rate_to_usd` | VARCHAR | — | decimal text with `.`; loaded as text, parsed in step 3 |

— `data-model.md §Entities, five raw.* tables, verbatim; typed views: see data-model.md §Views (not repeated here); staged pairs `migrations/01_create_raw_inputs.{up,down}.sql` and `migrations/02_create_typed_views.{up,down}.sql`` · full text: [data-model.md](../data-model.md)

## API contract

Internal — no API surface.

## Acceptance criteria

### AC-02 (US-03) — happy path

> **Given** the entries of both exports are loaded  
> **When** the Reviewer looks at the aligned entries  
> **Then** every entry from either source system shows the same attributes under the same names, with its description in one common language (a fixed, committed translation list, no external service), a real calendar date, a numeric amount, and one signed amount in which a debit is positive and a credit is negative, regardless of how its source wrote dates, numbers, debits and credits; in ERP A a debit or credit cell is filled when it is not empty (a cell holding zero counts as filled), and exactly one of the two is filled, with a number greater than zero, and in ERP B a positive amount is a debit and a negative amount is a credit; a description that has no entry in the translation list keeps its original text, its entry stays among the aligned entries (it is not an AC-09 case), and the description is written to the exceptions report (`exceptions_report.csv`), one record per aligned entry whose description has no translation, with the columns `source_system`, `source_document`, `source_line` and `original_description` (the same names as in the aligned entries), written to the build area on every run (with only its header when there is no such entry); a description is translated only when its whole text equals an entry of the translation list exactly (no word-level or case-insensitive matching), and the common language is English; missing exchange rates and reconciliation differences are not part of this report (rates belong to step 3, differences are reported by the completeness gate, AC-08)
>
> — `spec.md §5, AC-02, verbatim` · full text: [spec.md](../spec.md)

### AC-03 (US-04) — happy path

> **Given** an aligned entry from either source system  
> **When** the Reviewer checks where it came from  
> **Then** the entry names its source system, original document and original line, and the raw record found by that source system, document and line (the raw data is kept as it arrived, so for the nested-record export it stays nested) shows the same date, amount and local account as the aligned entry, where «same» means equal after reading the value in the format of its source
>
> — `spec.md §5, AC-03, verbatim` · full text: [spec.md](../spec.md)


## Checklist

- [ ] Promote `01_create_raw_inputs.up.sql` to `products/unified_gl/adapters/duckdb/01_create_raw_inputs.sql` (five `raw.*` tables, `read_csv` / `read_json`); keep the staged `.down.sql` beside it as documentation of the reverse — `products/unified_gl/adapters/duckdb/`
- [ ] Promote `02_create_typed_views.up.sql` to `adapters/duckdb/02_create_typed_views.sql` (`raw.typed_erp_a`, `raw.typed_erp_b`) — `products/unified_gl/adapters/duckdb/`
- [ ] Test (run from the repo root, `monkeypatch.chdir`): both files execute on an empty DuckDB with the three schemas; the raw tables hold the row counts of the files; ERP B lines stay nested — `tests/unit/test_adapter_duckdb.py`
- [ ] Test per deliberate source difference at view level (date formats, number formats, amount representation, column names): a sample row of each export reads into the typed view as the same DATE / DECIMAL under the same column names — `tests/unit/test_adapter_duckdb.py`
- [ ] Test unreadable values become NULL, never guessed: bad date, `1,234.56` in ERP A, three decimals, both debit and credit filled keeps both `*_filled` flags true — `tests/unit/test_adapter_duckdb.py`
- [ ] Do not edit the staged files in `docs/`; copy, then keep the copy in `adapters/duckdb/` as the live version — `docs/features/unified-gl-inputs/migrations/`

## Edge cases

| Case | Behaviour |
|---|---|
| Date `31.02.2026` in ERP A | `entry_date` NULL (not a real date), entry later reported as lost (AC-09) |
| ERP A debit `1.234,56` | DECIMAL 1234.56; the same value written `1,234.56` is NULL (wrong format) |
| ERP A debit and credit both filled | both `*_filled` true; neutral SQL rejects it, view does not guess |
| Amount with 3 decimals | NULL (more decimals than the currency allows) |
| Run started from another working directory | file paths are repo-root relative; the test and `fdp run` run from the root |
| `rates_synthetic.csv` | loaded into `raw.exchange_rate`, read by nothing in this step |

## Definition of Done

- [ ] Both adapter files execute on DuckDB; the pair applies and its `.down.sql` reverts cleanly (checked once against an in-memory DB)
- [ ] Adapter test passes for the five source differences at view level (AC-02, AC-03 raw side)
- [ ] Staged files promoted to the live adapter folder; no SQL outside `adapters/` reads files
- [ ] lint clean
- [ ] every Hard Rule inlined above still holds
- [ ] lint + vet clean
