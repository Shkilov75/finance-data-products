---
id: T4
title: "Test the committed inputs: reproducibility hash, size, quarter, keys, balance, currencies, daily rates, synthetic names"
layer: "tests"
deps: ["T3"]
blocks: ["T13"]
acs: ["AC-05", "AC-12"]
files_hint: ["tests/unit/test_inputs.py"]
owner: "maksym.shkilov@gmail.com"
estimate: "S"
context_budget: "S"
status: "done"
step: "COMMIT"
---

<!-- Self-contained task. Inlined chunks carry a provenance signature; the source always wins.
To the executing agent: work from what is inlined here. If a slice is insufficient, ambiguous, or contradicts the code in front of you, open the named file for the full text and follow that. Do not invent the missing part. -->

# T4 — Test the committed inputs: reproducibility hash, size, quarter, keys, balance, currencies, daily rates, synthetic names

## Place in the sequence

- **Blocked by:** T3 — Write the seeded data generator and commit the five synthetic input files · **Blocks:** T13 — End-to-end tests: five source differences, known values, traceability, exceptions report, exit codes · **Wave:** 2, after the files exist (T3).
- **Lane:** Own lane (one new test file).

## Why (user story)

> **As an** Owner  
> **I want** to generate both ERP exports, the account mapping, the description translation list and the exchange-rate file from a fixed seed, at a small readable size  
> **So that** every checkout has identical input data
>
> — `spec.md §4, US-01, verbatim` · full text: [spec.md](../spec.md)

Turns «every checkout has identical input data» into automated checks (the generator does not check itself).

## Inlined context

> The generator does **not** check its own output. Size (100 to 250 entries per export), the first quarter, explicit document and line numbers, balanced documents, currencies and one rate per currency per day are checked by the test suite (decision of the `api` run, 2026-11-06; report finding F3).
>
> — `contracts/cli.md §5 C3, verbatim` · full text: [contracts/cli.md](../contracts/cli.md)

> | Reproducibility | 100%: a fresh generation gives files byte-identical to the committed ones and to a second fresh generation, two runs give identical entry identifiers | test comparing file hashes and identifiers |
>
> — `spec.md §6, NFR table row, verbatim` · full text: [spec.md](../spec.md)

> | Readability of inputs | 100 to 250 entries per export (target ≈ 150) | test on the size of the committed files |
>
> — `spec.md §6, NFR table row, verbatim` · full text: [spec.md](../spec.md)

> every run writes only to the build area; only the generator writes the input files and a product run opens them read-only (AC-12)
>
> — `sad.md §6, Flow 3 final note, abridged` · full text: [sad.md](../sad.md)

**Fallback:** insufficient or contradicted by the code → read the named file in full ([spec.md](../spec.md) · [sad.md](../sad.md) · [data-model.md](../data-model.md) · [cli.md](../contracts/cli.md) · [adr/](../adr/)) and follow it. Do not guess.

## Data delta

No DB changes.

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

- [ ] Hash test: call the generator into `tmp_path` twice, compare file hashes with each other and with the committed files — `tests/unit/test_inputs.py`
- [ ] Parse the committed files with plain Python (`csv`, `json`, no DuckDB): 100–250 entries per export, dates inside 2026-01-01..2026-03-31, explicit document and line on every entry — `tests/unit/test_inputs.py`
- [ ] Per document: one currency, debits equal credits; currencies of both exports ⊇ {EUR, GBP, USD} — `tests/unit/test_inputs.py`
- [ ] Rates: exactly one row per (day, currency) for every day in the quarter and every currency used, USD rate 1 — `tests/unit/test_inputs.py`
- [ ] Names: every input file name contains `synthetic` — `tests/unit/test_inputs.py`

## Edge cases

| Case | Behaviour |
|---|---|
| Hand-edited input file | hash test names the file that differs |
| Rate missing for one currency on one day | test names currency and date |
| A document does not balance | test names the document |

## Definition of Done

- [ ] `pytest tests/unit/test_inputs.py` passes on the committed files (AC-05)
- [ ] Each check fails with a message naming the file/document/currency+date when the input is altered (verified once by a manual edit, then reverted)
- [ ] Every input file name contains `synthetic` (AC-12; the unchanged-after-a-run check lives in T13)
- [ ] lint clean
- [ ] every Hard Rule inlined above still holds
- [ ] lint + vet clean
