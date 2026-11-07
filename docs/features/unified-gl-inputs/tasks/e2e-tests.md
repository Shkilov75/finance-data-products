---
id: T13
title: "End-to-end tests: five source differences, known values, traceability, exceptions report, exit codes"
layer: "tests"
deps: ["T11", "T12", "T4"]
blocks: []
acs: ["AC-01", "AC-02", "AC-03", "AC-04", "AC-07", "AC-12", "AC-13", "AC-14"]
files_hint: ["tests/integration/test_unified_gl_run.py", "tests/integration/conftest.py"]
owner: "maksym.shkilov@gmail.com"
estimate: "M"
context_budget: "M"
status: "done"
step: "COMMIT"
---

<!-- Self-contained task. Inlined chunks carry a provenance signature; the source always wins.
To the executing agent: work from what is inlined here. If a slice is insufficient, ambiguous, or contradicts the code in front of you, open the named file for the full text and follow that. Do not invent the missing part. -->

# T13 — End-to-end tests: five source differences, known values, traceability, exceptions report, exit codes

## Place in the sequence

- **Blocked by:** T11 — Activate unified_gl: product.toml manifest, smoke-test update, timed CI run, T12 — Document the aligned entry attributes and the synthetic-data notice in the product README, T4 — Test the committed inputs: reproducibility hash, size, quarter, keys, balance, currencies, daily rates, synthetic names · **Blocks:** — · **Wave:** 6, last: needs the wired product (T11), README (T12), input checks (T4).
- **Lane:** Own lane (new files in `tests/integration/`).

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

Proves the whole chain: one test per deliberate difference, entries equal to the generator's known values, raw record traceable.

## Inlined context

> Verify QG-1: one automated test per deliberate source difference (dates, numbers, amount representation, column names, chart of accounts; spec §7); a test that compares `staging.ledger_entry` with the known values written by the generator, which covers a parsing error that both parsers of ADR-0002 would share.
>
> — `sad.md §10 QG-1, How verify, abridged` · full text: [sad.md](../sad.md)

> | Gate scenarios | 1 passing scenario for each of the 2 gates of this step (failing scenarios belong to step 4) | automated test suite |
>
> — `spec.md §6, NFR table row, verbatim` · full text: [spec.md](../spec.md)

> Deliberate source differences visibly resolved in the aligned entries — baseline 0 of 5 (dates, numbers, amount representation, column names, chart of accounts), target 5 of 5 by 2026-11-10, each shown by one automated test.
>
> — `spec.md §7 KPIs, abridged` · full text: [spec.md](../spec.md)

> Two runs give identical entry identifiers (test comparing file hashes and identifiers); the run summary lists exactly the transaction currencies that occur in the entries.
>
> — `spec.md §6 Reproducibility + AC-14, abridged` · full text: [spec.md](../spec.md)

> Gate-failing scenarios on corrupted data (the `corrupt(...)` helper, `make demo-bad`) belong to roadmap step 4 and are NOT built here; this task only proves the clean run.
>
> — `spec.md §3 Non-goals + data-model.md §Test fixtures, abridged` · full text: [spec.md](../spec.md)

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

### AC-03 (US-04) — happy path

> **Given** an aligned entry from either source system  
> **When** the Reviewer checks where it came from  
> **Then** the entry names its source system, original document and original line, and the raw record found by that source system, document and line (the raw data is kept as it arrived, so for the nested-record export it stays nested) shows the same date, amount and local account as the aligned entry, where «same» means equal after reading the value in the format of its source
>
> — `spec.md §5, AC-03, verbatim` · full text: [spec.md](../spec.md)

### AC-04 (US-05) — happy path

> **Given** a local account that appears in the account mapping for its source system  
> **When** an entry that uses it is aligned  
> **Then** the entry carries the group account assigned to that local account for that source system, and the same local account code in the other source system can map to a different group account without affecting it
>
> — `spec.md §5, AC-04, verbatim` · full text: [spec.md](../spec.md)

### AC-07 (US-06) — happy path

> **Given** clean data loaded from both exports  
> **When** the completeness gate runs  
> **Then** it passes because, for each source system and transaction currency, the number of entries and the total of debits and credits in the raw data equal those in the aligned entries, and every raw entry, matched by source system, document and line, has exactly one aligned entry with the same date, signed amount and local account; the raw-side counts and totals are obtained from the loaded raw records by a separate reading, written independently of the alignment and not reusing its parsing; a record lost while the files are loaded is caught by a separate test that compares the number of records in each file with the number loaded
>
> — `spec.md §5, AC-07, verbatim` · full text: [spec.md](../spec.md)

### AC-12 (US-01) — authorization

> **Given** a Reviewer with a fresh clone and no accounts or credentials of any kind  
> **When** the Reviewer runs the product  
> **Then** the run succeeds using only the committed files, leaves every committed input file (both exports, the account mapping, the translation list and the exchange-rate file) unchanged, and every name and amount in them is fictitious, with the README next to the committed files and the name of each of these input files stating that the data is synthetic
>
> — `spec.md §5, AC-12, verbatim` · full text: [spec.md](../spec.md)

### AC-13 (US-06) — cross-context

> **Given** the product is declared active and the other three products are declared reserved (no gates yet), as defined in the glossary  
> **When** the Reviewer runs the whole repository  
> **Then** the failure of either gate of this product makes the overall run end as not successful, while the reserved products are listed as reserved in the run output and do not affect the result
>
> — `spec.md §5, AC-13, verbatim` · full text: [spec.md](../spec.md)

### AC-14 (US-07) — cross-context

> **Given** the next step needs an exchange rate for every transaction currency that is present  
> **When** the Owner reads the product documentation of the aligned entries  
> **Then** it lists every attribute of an aligned entry with its meaning (at least the identifier, source system, document, line, date, signed amount, transaction currency, local account, group account, description in the common language and original description), and the run summary lists exactly the transaction currencies that occur in the entries
>
> — `spec.md §5, AC-14, verbatim` · full text: [spec.md](../spec.md)


## Checklist

- [ ] Fixture: run `fdp` main from the repo root once per session (`conftest.py`), keep stdout and the read-only DuckDB connection — `tests/integration/conftest.py`
- [ ] Five tests, one per difference: dates (`DD.MM.YYYY` / `MM/DD/YYYY` → same DATE), numbers (`1.234,56` / `-1,234.56` → DECIMAL), amount representation (debit+credit columns vs signed → one signed amount), column names (same attribute names), chart of accounts (different local codes → group accounts) — `tests/integration/test_unified_gl_run.py`
- [ ] Known-values test: every row of `staging.ledger_entry` equals the expected entries returned by `generate()` (id, signed amount, group account, description) — `tests/integration/test_unified_gl_run.py`
- [ ] Traceability test: for a sample of entries find the raw record by source system, document, line and compare date, amount, local account after parsing the source format — `tests/integration/test_unified_gl_run.py`
- [ ] Run-output tests: summary rows per source system and currency, currencies equal the entry currencies, `exceptions_report.csv: <n> records` printed and file present, both gates PASS, reserved products listed, exit 0 (AC-01, AC-13, AC-14) — `tests/integration/test_unified_gl_run.py`
- [ ] Exceptions report content test: columns and the untranslated ERP A descriptions only (AC-02) — `tests/integration/test_unified_gl_run.py`
- [ ] Read-only test (AC-12): hash the five committed input files before and after the run, assert equal; assert the run wrote only under `build/` — `tests/integration/test_unified_gl_run.py`
- [ ] Confirm `make test` runs the integration folder (check `pyproject.toml` testpaths) — `pyproject.toml`

## Edge cases

| Case | Behaviour |
|---|---|
| Run started from another directory | fixture changes to the repo root before running |
| Gate failure scenario | not tested here (roadmap step 4) |
| Test depends on generator order | expected entries come from `generate()`, not from the SQL under test |

## Definition of Done

- [ ] Five source-difference tests, the known-values test and the traceability test pass (AC-02, AC-03, AC-04)
- [ ] Run-output test: summary, exceptions line, both gates PASS, reserved products listed (AC-01, AC-07, AC-13, AC-14); input files unchanged after the run (AC-12)
- [ ] `make test` green, run time of the suite acceptable (< 30 s of `make run` itself)
- [ ] lint clean
- [ ] every Hard Rule inlined above still holds
- [ ] lint + vet clean
