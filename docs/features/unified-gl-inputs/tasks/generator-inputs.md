---
id: T3
title: "Write the seeded data generator and commit the five synthetic input files"
layer: "infra"
deps: []
blocks: ["T4", "T5"]
acs: ["AC-05", "AC-12"]
files_hint: ["products/unified_gl/data/generate.py", "products/unified_gl/data/"]
owner: "maksym.shkilov@gmail.com"
estimate: "L"
context_budget: "M"
status: "done"
step: "COMMIT"
---

<!-- Self-contained task. Inlined chunks carry a provenance signature; the source always wins.
To the executing agent: work from what is inlined here. If a slice is insufficient, ambiguous, or contradicts the code in front of you, open the named file for the full text and follow that. Do not invent the missing part. -->

# T3 — Write the seeded data generator and commit the five synthetic input files

## Place in the sequence

- **Blocked by:** — · **Blocks:** T4 — Test the committed inputs: reproducibility hash, size, quarter, keys, balance, currencies, daily rates, synthetic names, T5 — Create the DuckDB adapter files: raw load of the five inputs and the typed views · **Wave:** 1, no upstream dependency; unblocks the adapter, the tests and the input checks.
- **Lane:** Own lane (touches only `products/unified_gl/data/`); runs in parallel with T1.

## Why (user story)

> **As an** Owner  
> **I want** to generate both ERP exports, the account mapping, the description translation list and the exchange-rate file from a fixed seed, at a small readable size  
> **So that** every checkout has identical input data
>
> — `spec.md §4, US-01, verbatim` · full text: [spec.md](../spec.md)

Delivers the committed, reproducible inputs that every other task reads.

## Inlined context

> | Arguments | none. The seed is fixed in the script (AC-05) |
> | Writes | the five input files named in §3.2, into `products/unified_gl/data/`; every file name contains `synthetic` (AC-12) |
> | Output on stdout | `erp_a_export_synthetic.csv: <n> entries` and `erp_b_export_synthetic.json: <n> entries` |
> | Exit | 0 files written; 3 a file could not be written |
> | Determinism | byte-identical files on every call: amounts from integer cents, no timestamps, fixed row and key order, LF endings (spec §6) |
> | Python API | also returns the list of expected aligned entries (`entry_id`, signed amount, group account, common description) for tests |
> The generator does **not** check its own output. Size, the first quarter, explicit document and line numbers, balanced documents, currencies and one rate per currency per day are checked by the test suite (T4).
>
> — `cli.md §5 C3 data generator, verbatim` · full text: [cli.md](../contracts/cli.md)

> Fixed seed, amounts built from integer cents (no floating point), no timestamps, fixed row order and key order, LF line endings; checked by a file-hash test
>
> — `sad.md §8, Determinism of generated data, verbatim` · full text: [sad.md](../sad.md)

> **ADR-0005 (feature), decision:** Option 1. A pretty-printed document with its lines nested under it is the form a Reviewer reads most easily and the closest to «nested records». DuckDB reads it with `read_json`; Spark needs the `multiLine` option, which is one setting in the Databricks adapter. Option 2 reads on Spark without options and diffs better in git, but a full document on one line is hard to read by eye.
>
> — `adr/0005-store-the-nested-erp-export-as-a-json-array-of-documents.md, Decision outcome, verbatim` · full text: [adr/0005-store-the-nested-erp-export-as-a-json-array-of-documents.md](../adr/0005-store-the-nested-erp-export-as-a-json-array-of-documents.md)

> Clean data: about 150 entries per export, Q1 2026, EUR/GBP/USD, balanced documents, at least one local account code that occurs in both charts with different group accounts (AC-04), a few ERP A descriptions without a translation row so that the exceptions report is non-empty on clean data (AC-01).
>
> — `data-model.md §Test fixtures, Clean data, verbatim` · full text: [data-model.md](../data-model.md)

> ERP B is already in English, so the generator writes identity rows (`original = common`) for its descriptions. … ERP A is German, ERP B is English, the common language is English.
>
> — `data-model.md §Entities (description_translation design note) and header, abridged` · full text: [data-model.md](../data-model.md)

> Date `DD.MM.YYYY`, number `1.234,56` (thousands `.`, decimal `,`), exactly one of debit and credit filled. [ERP A: delimiter `;`, header row, UTF-8, LF, German column names]  ·  Date `MM/DD/YYYY`, number `-1,234.56` (thousands `,`, decimal `.`, leading `-` for a credit). All JSON values are strings. [ERP B: one pretty-printed JSON array of document objects, English field names, fixed key order]
>
> — `data-model.md §Entities, raw.erp_a_export + raw.erp_b_export file lines, abridged` · full text: [data-model.md](../data-model.md)

> Shared behaviour lives in `src/fdp_core/`, never copied into a product. Products never import each other. IDs are deterministic hashes of business keys, never random UUIDs.
>
> — `CLAUDE.md §Conventions, abridged` · full text: [../../../CLAUDE.md](../../../../CLAUDE.md)

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

— `data-model.md §Entities, tables raw.erp_a_export / raw.erp_b_export / raw.account_mapping / raw.description_translation / raw.exchange_rate, verbatim (the generator writes these files; it creates no DB table)` · full text: [data-model.md](../data-model.md)

## API contract

Internal — no API surface.

## Acceptance criteria

### AC-05 (US-01) — happy path

> **Given** the Owner generates the exports, the account mapping, the description translation list (`description_translation_synthetic.csv` in the product's data folder) and the exchange-rate file (`rates_synthetic.csv` in the product's data folder, with the columns date, currency and rate_to_usd) with the fixed seed  
> **When** the Owner generates them a second time  
> **Then** the files are identical to the first time, each export holds between 100 and 250 entries (target about 150), all dated within the first quarter of 2026 (January to March), both exports carry an explicit document number and line number for every entry, the two exports together use at least EUR, GBP and USD as transaction currencies, and every document is posted in one transaction currency and balances: its debits equal its credits, and the rate file holds exactly one rate to USD for each transaction currency that occurs in the exports (USD included, with the rate 1) on every calendar day from 2026-01-01 to 2026-03-31
>
> — `spec.md §5, AC-05, verbatim` · full text: [spec.md](../spec.md)

### AC-12 (US-01) — authorization

> **Given** a Reviewer with a fresh clone and no accounts or credentials of any kind  
> **When** the Reviewer runs the product  
> **Then** the run succeeds using only the committed files, leaves every committed input file (both exports, the account mapping, the translation list and the exchange-rate file) unchanged, and every name and amount in them is fictitious, with the README next to the committed files and the name of each of these input files stating that the data is synthetic
>
> — `spec.md §5, AC-12, verbatim` · full text: [spec.md](../spec.md)


## Checklist

- [ ] `generate.py`: fixed seed, integer cents, `random.Random(seed)`, no timestamps, LF; `main()` writes the five files and prints the two stdout lines; `generate()` returns the expected aligned entries — `products/unified_gl/data/generate.py`
- [ ] ERP A rows: German names, `DD.MM.YYYY`, `1.234,56`, debit/credit columns, explicit `belegnummer` and `zeile`; ERP B documents: English names, `MM/DD/YYYY`, signed `amount`, nested `lines` with `line_no`; one currency per document, every document balanced — `generate.py`
- [ ] Two charts of accounts with at least one local account code present in both with different group accounts; account mapping covers every used account — `generate.py`
- [ ] Translation list: German→English rows for ERP A, identity rows for ERP B, a few ERP A descriptions deliberately left out (non-empty exceptions report on clean data) — `generate.py`
- [ ] Rates: EUR, GBP, USD (USD = 1) for every day 2026-01-01..2026-03-31 — `generate.py`
- [ ] Expected-entry list computed from the generator's own model with `entry_id = md5(source_system|document|int(line))` — `generate.py`
- [ ] Run it, commit the five files `erp_a_export_synthetic.csv`, `erp_b_export_synthetic.json`, `account_mapping_synthetic.csv`, `description_translation_synthetic.csv`, `rates_synthetic.csv`; keep `.gitkeep` or remove it — `products/unified_gl/data/`

## Edge cases

| Case | Behaviour |
|---|---|
| Generator run twice | byte-identical files (hash test in T4) |
| Document with lines in more than one currency | must not occur: one currency per document (AC-05) |
| Amount with a third decimal place | must not be generated on clean data; any such value is an AC-09 case for step 4 |
| File name without `synthetic` | not allowed (AC-12) |

## Definition of Done

- [ ] `python products/unified_gl/data/generate.py` prints both counts, exit 0, and a second run leaves `git diff` empty
- [ ] Each export holds 100–250 entries, all dated Jan–Mar 2026; EUR, GBP, USD present; every document balances
- [ ] Five committed files, every name contains `synthetic`
- [ ] No real names or amounts; lint clean
- [ ] every Hard Rule inlined above still holds
- [ ] lint + vet clean
