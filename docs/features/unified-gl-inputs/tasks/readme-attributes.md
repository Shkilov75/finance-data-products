---
id: T12
title: "Document the aligned entry attributes and the synthetic-data notice in the product README"
layer: "docs"
deps: ["T7"]
blocks: ["T13"]
acs: ["AC-12", "AC-14"]
files_hint: ["products/unified_gl/README.md"]
owner: "maksym.shkilov@gmail.com"
estimate: "S"
context_budget: "M"
status: "todo"
step: ""
---

<!-- Self-contained task. Inlined chunks carry a provenance signature; the source always wins.
To the executing agent: work from what is inlined here. If a slice is insufficient, ambiguous, or contradicts the code in front of you, open the named file for the full text and follow that. Do not invent the missing part. -->

# T12 — Document the aligned entry attributes and the synthetic-data notice in the product README

## Place in the sequence

- **Blocked by:** T7 — Create staging.ledger_entry: the aligned entry set (neutral SQL) · **Blocks:** T13 — End-to-end tests: five source differences, known values, traceability, exceptions report, exit codes · **Wave:** 4, needs the final column list from T7.
- **Lane:** Own lane (one file); runs in parallel with T8–T10.

## Why (user story)

> **As an** Owner  
> **I want** the aligned entry set to have a documented, stable shape and identifiers that do not change between runs  
> **So that** the USD conversion step can build on it without rework
>
> — `spec.md §4, US-07, verbatim` · full text: [spec.md](../spec.md)

Delivers the documented, stable shape of the aligned entry set that step 3 builds on.

## Inlined context

> The Owner reads the product documentation of the aligned entries. It lists every attribute of an aligned entry with its meaning (at least the identifier, source system, document, line, date, signed amount, transaction currency, local account, group account, description in the common language and original description). The README sits next to the committed files and says the data is synthetic.
>
> — `spec.md §5, AC-14 + AC-12, abridged` · full text: [spec.md](../spec.md)

> The Reviewer sees the aligned entries by opening `build/fdp.duckdb` and reading the table `staging.ledger_entry` (for example with the `duckdb` command line client). There is no command and no CSV export for it in this step. Sample output for the reader belongs to roadmap step 5.
>
> — `contracts/cli.md §7 Data contract, abridged` · full text: [contracts/cli.md](../contracts/cli.md)

> Reports are written also when a gate fails; the README says so explicitly, and `build/` holds diagnostics only. No Databricks compatibility claim in the README before a real run. The refinement «adapters live in `products/unified_gl/adapters/<engine>/`» should be mentioned.
>
> — `sad.md §11 (reports risk + view-contract risk) and §1 override, abridged` · full text: [sad.md](../sad.md)

> Traceability (AC-03): the raw record is found by `source_system`, `source_document`, `source_line` in `raw.erp_a_export` (`belegnummer`, `zeile`) or `raw.erp_b_export` (`doc_id`, nested `lines[].line_no`).
>
> — `contracts/cli.md §7, verbatim` · full text: [contracts/cli.md](../contracts/cli.md)

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

— `data-model.md §Entities, staging.ledger_entry, verbatim (read-only for this task; the README documents it)` · full text: [data-model.md](../data-model.md)

## API contract

Internal — no API surface.

## Acceptance criteria

### AC-12 (US-01) — authorization

> **Given** a Reviewer with a fresh clone and no accounts or credentials of any kind  
> **When** the Reviewer runs the product  
> **Then** the run succeeds using only the committed files, leaves every committed input file (both exports, the account mapping, the translation list and the exchange-rate file) unchanged, and every name and amount in them is fictitious, with the README next to the committed files and the name of each of these input files stating that the data is synthetic
>
> — `spec.md §5, AC-12, verbatim` · full text: [spec.md](../spec.md)

### AC-14 (US-07) — cross-context

> **Given** the next step needs an exchange rate for every transaction currency that is present  
> **When** the Owner reads the product documentation of the aligned entries  
> **Then** it lists every attribute of an aligned entry with its meaning (at least the identifier, source system, document, line, date, signed amount, transaction currency, local account, group account, description in the common language and original description), and the run summary lists exactly the transaction currencies that occur in the entries
>
> — `spec.md §5, AC-14, verbatim` · full text: [spec.md](../spec.md)


## Checklist

- [ ] Add the section «Aligned entries» with a table of the 11 attributes copied from the data-model table (name, type, meaning, NULL rule) — `products/unified_gl/README.md`
- [ ] State at the top that every input file and every name and amount in it is synthetic, list the five file names — `products/unified_gl/README.md`
- [ ] Explain gate vs invariant check vs exceptions report, the exit codes 0/1/2/3, where reports land (`build/`), and that reports are also written after a failed gate — `products/unified_gl/README.md`
- [ ] Describe how to trace an entry to its raw record and how to open `build/fdp.duckdb`; list the five deliberate source differences — `products/unified_gl/README.md`
- [ ] Mention the adapters folder layout and that `adapters/databricks/` is not yet written or verified — `products/unified_gl/README.md`

## Edge cases

| Case | Behaviour |
|---|---|
| A column is added later to `staging.ledger_entry` | README table and data-model must change together (source: data-model.md wins) |
| Reader expects a CSV of the aligned entries | README says there is none in this step |

## Definition of Done

- [ ] README lists all 11 attributes with meaning, matching `data-model.md` column names exactly (AC-14)
- [ ] README and the five file names state the data is synthetic (AC-12)
- [ ] No claim of Databricks compatibility
- [ ] Markdown links resolve
- [ ] every Hard Rule inlined above still holds
- [ ] lint + vet clean
