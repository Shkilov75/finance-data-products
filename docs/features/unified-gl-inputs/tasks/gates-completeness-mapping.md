---
id: T9
title: "Write the completeness gate and the mapping gate"
layer: "domain"
deps: ["T6", "T7"]
blocks: ["T11"]
acs: ["AC-07", "AC-08", "AC-09", "AC-10"]
files_hint: ["products/unified_gl/gates/01_completeness.sql", "products/unified_gl/gates/02_mapping.sql", "tests/unit/test_gates.py"]
owner: "maksym.shkilov@gmail.com"
estimate: "M"
context_budget: "M"
status: "done"
step: "COMMIT"
---

<!-- Self-contained task. Inlined chunks carry a provenance signature; the source always wins.
To the executing agent: work from what is inlined here. If a slice is insufficient, ambiguous, or contradicts the code in front of you, open the named file for the full text and follow that. Do not invent the missing part. -->

# T9 — Write the completeness gate and the mapping gate

## Place in the sequence

- **Blocked by:** T6 — Create the control views (independent raw side of the completeness gate), T7 — Create staging.ledger_entry: the aligned entry set (neutral SQL) · **Blocks:** T11 — Activate unified_gl: product.toml manifest, smoke-test update, timed CI run · **Wave:** 4, needs the control views (T6) and the entry table (T7); parallel to T8 and T10.
- **Lane:** Own lane (new gate files; `.gitkeep` removed).

## Why (user story)

> **As a** Reviewer  
> **I want** to see a gate that fails when an entry or an amount is lost between the raw files and the aligned entries  
> **So that** I can trust the alignment
>
> — `spec.md §4, US-06, verbatim` · full text: [spec.md](../spec.md)

> **As a** Reviewer  
> **I want** to see every entry carry the group account its local account maps to, and see any entry whose local account has no mapping  
> **So that** no entry silently disappears or lands in a blank account
>
> — `spec.md §4, US-05, verbatim` · full text: [spec.md](../spec.md)

Delivers the two gates the Reviewer trusts: nothing lost on the way, no entry without a group account.

## Inlined context

> **ADR-0002 (feature), decision:** Option 1. It keeps the completeness gate a plain SQL file that returns the violating rows, runs on both engines through the existing adapter mechanism, and still has a separate code path for the raw side. Option 2 gives stronger independence but works only where the raw files are on the local disk, so step 6 would need a rewrite or a file-access layer, and the gate would stop following the one-SQL-file convention.
>
> — `adr/0002-compute-completeness-controls-on-an-independent-path.md, Decision outcome, verbatim` · full text: [adr/0002-compute-completeness-controls-on-an-independent-path.md](../adr/0002-compute-completeness-controls-on-an-independent-path.md)

> Per source system and transaction currency compare the entry count, debit total and credit total of the raw side and the aligned side; compare every raw entry matched by source system, document and line with its aligned entry for date, signed amount and local account. The result lists rows naming source system, currency and the difference, and source system, document and line of each entry that is missing or differs. An unreadable entry counts in the raw entry count and adds nothing to the raw totals so it shows as missing; two entries that exchanged amounts leave the totals unchanged and are found by the entry comparison.
>
> — `sad.md §6, Flow 6 «Completeness gate on an independent control path», abridged` · full text: [sad.md](../sad.md)

> The gate derives the raw debit total as the sum of positive `signed_amount`, the raw credit total as the sum of the negated negative values … The reconciliation gate never uses a signed total (balanced documents sum to zero, so it could never fail): this step compares total debits and total credits separately.
>
> — `data-model.md §Views control views + spec.md §3 Non-goals, abridged` · full text: [data-model.md](../data-model.md)

> Accuracy of the completeness gate on clean data: 0 differences in entry count and in totals; amounts are fixed-precision decimals with 2 decimal places, never rounded.
>
> — `spec.md §6, NFR «Accuracy of the completeness gate», abridged` · full text: [spec.md](../spec.md)

> completeness rows name source system, transaction currency and the difference in entry count, debit total or credit total, and source system, document and line of each entry that is missing or differs; mapping rows name source system and local account.
>   ERP_A EUR entries: raw 61, aligned 60
>   ERP_A EUR debit_total: raw 48210.40, aligned 48110.40
>   ERP_A DOC-0007 line 2: missing in aligned entries
>
> — `cli.md §3.3 item 3 and exit-1 example, abridged` · full text: [cli.md](../contracts/cli.md)

> `staging.ledger_entry (group_account)` — mapping gate: rows with NULL `group_account` (AC-10)
>
> — `data-model.md §Indexes, Mapping gate, verbatim` · full text: [data-model.md](../data-model.md)

> A gate is one SQL file `products/<p>/gates/NN_<name>.sql`; zero returned rows means PASS. A failed gate is a result, not an exception; the runner exits non-zero on any FAIL.
>
> — `CLAUDE.md §Conventions, abridged` · full text: [../../../CLAUDE.md](../../../../CLAUDE.md)

> Product SQL is dialect-neutral (runs on DuckDB and Spark SQL); engine differences go into an adapter — repo ADR-0004.
>
> — `sad.md §2 Constraints, Technical, abridged` · full text: [sad.md](../sad.md)

**Fallback:** insufficient or contradicted by the code → read the named file in full ([spec.md](../spec.md) · [sad.md](../sad.md) · [data-model.md](../data-model.md) · [cli.md](../contracts/cli.md) · [adr/](../adr/)) and follow it. Do not guess.

## Data delta

No DB changes.

## API contract

Internal — no API surface.

## Acceptance criteria

### AC-07 (US-06) — happy path

> **Given** clean data loaded from both exports  
> **When** the completeness gate runs  
> **Then** it passes because, for each source system and transaction currency, the number of entries and the total of debits and credits in the raw data equal those in the aligned entries, and every raw entry, matched by source system, document and line, has exactly one aligned entry with the same date, signed amount and local account; the raw-side counts and totals are obtained from the loaded raw records by a separate reading, written independently of the alignment and not reusing its parsing; a record lost while the files are loaded is caught by a separate test that compares the number of records in each file with the number loaded
>
> — `spec.md §5, AC-07, verbatim` · full text: [spec.md](../spec.md)

### AC-08 (US-06) — error

> **Given** an entry is missing from the aligned entries, or its amount differs from the raw data  
> **When** the completeness gate runs  
> **Then** it fails, names the source system, the transaction currency and the difference in entry count, debit total or credit total, and names the source system, document and line of every entry that is missing or whose date, amount or local account differs (including two entries that exchanged amounts, which leave the totals unchanged), and the run ends as not successful; the completeness gate is one gate, and its result lists both kinds of difference (counts and totals per source system and transaction currency, and individual entries)
>
> — `spec.md §5, AC-08, verbatim` · full text: [spec.md](../spec.md)

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

- [ ] `01_completeness.sql`: one gate, two result kinds in one `UNION ALL` of rows — (a) per `source_system, transaction_currency`: difference in entry count, debit total, credit total between `raw.control_*` and `staging.ledger_entry`; (b) per entry matched by `source_system, document, line`: missing in aligned, or `entry_date` / `signed_amount` / `local_account` differs. Columns: `source_system`, `transaction_currency`, `document`, `line`, `kind`, `raw_value`, `aligned_value` (NULL where not applicable) — `products/unified_gl/gates/01_completeness.sql`
- [ ] `02_mapping.sql`: rows of `staging.ledger_entry` with `group_account IS NULL`, distinct on `source_system, local_account` — `products/unified_gl/gates/02_mapping.sql`
- [ ] Gate-passing scenarios on the clean generator data: both gates return zero rows (the spec's «1 passing scenario for each of the 2 gates») — `tests/unit/test_gates.py`
- [ ] Behaviour tests on tmp copies (not the step-4 demo data): delete one aligned entry → count and total rows plus a «missing» row naming source system, document, line; swap the amounts of two aligned entries → totals equal but two «differs» rows; unreadable raw entry → shows as missing; unmapped account → mapping rows naming source system and local account — `tests/unit/test_gates.py`
- [ ] Test that a raw file with fewer records than expected is caught by the load-count test (records in each file vs records loaded) — `tests/unit/test_gates.py`

## Edge cases

| Case | Behaviour |
|---|---|
| Two entries exchanged amounts | totals equal, entry comparison reports both entries (AC-08) |
| Unreadable raw entry | counts in raw entry count, nothing in raw totals → shows as a missing entry (AC-09) |
| Entry missing and another has a wrong amount | both listed; counts and totals rows also present |
| Aligned entry with no raw counterpart | reported as a difference (entry in aligned set but not in raw) |
| Same unmapped account in several entries | mapping gate names source system and local account once |
| Record lost while loading the file | caught by the separate load-count test, not by the gate |

## Definition of Done

- [ ] Both gates return zero rows on the committed clean data (AC-07)
- [ ] Behaviour tests for missing entry, wrong amount, swapped amounts, unreadable entry and unmapped account pass (AC-08, AC-09, AC-10)
- [ ] Gate files follow the one-SQL-file, zero-rows-is-PASS convention and contain no engine-specific construct
- [ ] lint clean
- [ ] every Hard Rule inlined above still holds
- [ ] lint + vet clean
