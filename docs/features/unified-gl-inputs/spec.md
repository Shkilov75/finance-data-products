---
status: Draft
owner: "maksym.shkilov@gmail.com"
reviewers: []
updated_at: "2026-11-04"
feature_size: "M"
---

# Spec — unified-gl-inputs

> **Glossary:** [CONTEXT](../../../CONTEXT.md) (project-wide, repo root)
> **Reference module / docs / channels used:** `docs/idea-brief.md` (§2, §4–§8), `docs/roadmap.md` (step 2), `docs/architecture-map.md`, ADR-0001 to ADR-0004; no external channels beyond that.

## 1. Context

The Owner is building a portfolio repository whose first data product, Unified GL, must turn two ERP exports into one consistent ledger. This feature is the first slice of that product (roadmap step 2): two synthetic ERP exports that visibly differ from each other are brought into the repository and aligned into one common set of ledger entries, still in each entry's transaction currency. Everything that follows (USD conversion, the two mandated gates, the published result) starts from this set, so it has to be complete and trustworthy before they are built. The audience is the Reviewer, who reads the repository without the author (idea-brief §2) and may then watch a live run.

The Reviewer's interview is about a week after 2026-11-04 (owner-reported, exact date unknown), and the whole repository has a budget of 10+ hours (idea-brief §4). The later steps cannot start until this one delivers a stable entry set.

The committed approach follows the direction the Owner accepted in idea-brief §7 (four products, a local run and a second execution path) and the decisions taken in the specification interview of 2026-11-04: the data is synthetic and generated reproducibly; the first export is a flat tabular text file and the second a nested-record file; they differ in date format, number format, amount representation (separate debit and credit columns versus one signed amount), column names and language, and chart of accounts. A third input, the account mapping, ties every local account to a group account. The aligned result carries every ledger entry once, tagged with its source system, with its original amounts. Two gates guard the result: a completeness gate checks that no entry or amount was lost on the way, and a mapping gate checks that every entry has a group account. Two findings shaped this: real general-ledger exports identify an entry by document plus line and show both debit/credit and signed-amount styles, which makes the chosen differences credible (researcher fact-check, 2026-11-04, source limits in ¶4); and a gate that only counts rows can pass on wrong data, so the completeness gate also compares control totals (devil's-advocate vector V1), while an entry with no mapping would vanish or sit unnoticed without its own gate (vector V2).

Traceability: idea-brief §5 fixes synthetic data and the demo purpose; §6 risk 1 (time budget) and risk 2 (Databricks access unknown) still stand. Evidence limits: the document-plus-line and debit/credit facts rest on SAP-style table documentation and NetSuite-style import documentation, read on 2026-11-04; the Dynamics-style family could not be verified; date and number formats of real exports are not sourced and are treated as locale conventions. Decision overrides from the critic pass land here as «Decision override: <headline> — rationale: <reason>» bullets.

- Decision override: this step carries two gates, not the one extra gate the Owner first accepted in the interview — rationale: the Owner chose a separate mapping gate after seeing that an unmapped entry would otherwise pass silently; the completeness gate also gained control totals.

## 2. Goals

- A Reviewer can run one command and see that both ERP exports were loaded completely and now exist as one common set of ledger entries, each traceable to its source system.
- Every deliberate difference between the two exports (dates, numbers, amount representation, column names, accounts) is visibly resolved, so a Reviewer can follow a sample entry from its raw form to its aligned form.
- The step stands on its own: reproducible data, a completeness gate and a mapping gate that fail when entries or amounts are lost or an entry has no group account, and a documented entry set that the next step (USD conversion and the mart) can build on without rework.

## 3. Non-goals

- Currency conversion, using the exchange rates, and the two mandated gates (rate exists on date, totals reconcile before and after conversion) — they belong to roadmap step 3; this step only generates the rates file (AC-05) and does not read it.
- Deliberately corrupted data and the proof that gates fail — roadmap step 4; this step only guarantees that the clean data passes.
- Running or claiming compatibility on a second execution platform — roadmap step 6 and open decision D1 (access unknown); this step keeps its logic portable but verifies nothing there.
- Reader documentation, diagrams and sample output — roadmap step 5.
- Reversal entries written as negative debit or credit values, and zero-amount entries — both are treated as unreadable (AC-09), not supported.
- Real ERP connections, real financial data, incremental loads or production hardening — the repository is a synthetic-data demo (idea-brief §5).

## 4. User stories

### US-01: Generate reproducible exports

**As an** Owner
**I want** to generate both ERP exports, the account mapping and the exchange-rate file from a fixed seed, at a small readable size
**So that** every checkout has identical input data

### US-02: See what each source delivered

**As a** Reviewer
**I want** to run one command and see how many entries each source system delivered in each transaction currency
**So that** I can tell at a glance that the data arrived

### US-03: See one common entry shape

**As a** Reviewer
**I want** to see the entries of both exports in one common shape (same names, dates, numbers and one amount convention)
**So that** I can compare them without knowing either ERP

### US-04: Trace an entry to its source

**As a** Reviewer
**I want** to see for every aligned entry the source system, original document and original line it came from
**So that** I can check the alignment against the raw file

### US-05: See entries mapped to group accounts

**As a** Reviewer
**I want** to see every entry carry the group account its local account maps to, and see any entry whose local account has no mapping
**So that** no entry silently disappears or lands in a blank account

### US-06: Trust the completeness gate

**As a** Reviewer
**I want** to see a gate that fails when an entry or an amount is lost between the raw files and the aligned entries
**So that** I can trust the alignment

### US-07: Hand over a stable entry set

**As an** Owner
**I want** the aligned entry set to have a documented, stable shape and identifiers that do not change between runs
**So that** the USD conversion step can build on it without rework

## 5. Acceptance criteria

<!-- Coverage note: authorization has no user permissions to check in this product; the access rule is that a run needs no accounts and cannot alter its source files (AC-12). -->

### AC-01 (US-02) — happy path

**Given** the Reviewer has a fresh clone of the repository, has done the one-time setup, and the product's exports are present
**When** the Reviewer starts the single run command
**Then** the run finishes successfully and prints, for each source system and each transaction currency, the number of entries loaded and their debit total and credit total, and states that both gates of the product passed

### AC-02 (US-03) — happy path

**Given** the entries of both exports are loaded
**When** the Reviewer looks at the aligned entries
**Then** every entry from either source system shows the same attributes under the same names, with its description in one common language (a fixed, committed translation list, no external service), a real calendar date, a numeric amount, and one signed amount in which a debit is positive and a credit is negative, regardless of how its source wrote dates, numbers, debits and credits; in ERP A exactly one of the debit and credit columns is filled with a non-negative number, and in ERP B a positive amount is a debit and a negative amount is a credit

### AC-03 (US-04) — happy path

**Given** an aligned entry from either source system
**When** the Reviewer checks where it came from
**Then** the entry names its source system, original document and original line, and the raw record found by that source system, document and line (the raw data is kept as it arrived, so for the nested-record export it stays nested) shows the same date, amount and local account as the aligned entry, where «same» means equal after reading the value in the format of its source

### AC-04 (US-05) — happy path

**Given** a local account that appears in the account mapping for its source system
**When** an entry that uses it is aligned
**Then** the entry carries the group account assigned to that local account for that source system, and the same local account code in the other source system can map to a different group account without affecting it

### AC-05 (US-01) — happy path

**Given** the Owner generates the exports, the account mapping and the exchange-rate file (`rates.csv` in the product's data folder, with the columns date, currency and rate_to_usd) with the fixed seed
**When** the Owner generates them a second time
**Then** the files are identical to the first time, each export holds between 100 and 250 entries (target about 150), all dated within the first quarter of 2026 (January to March), both exports carry an explicit document number and line number for every entry, the two exports together use at least EUR, GBP and USD as transaction currencies, and every document is posted in one transaction currency and balances: its debits equal its credits, and the rate file holds exactly one rate to USD for each transaction currency that occurs in the exports on each calendar date of the same quarter

### AC-06 (US-07) — domain invariant violation

**Given** aligned entries from both source systems, including two entries of one document that share date, account and amount, and both exports carry an explicit document number and line number for every entry
**When** the Owner runs the product twice
**Then** every entry has an identifier derived from source system, document and line, the identifiers are unique across both source systems, each entry keeps the same identifier in both runs, and if two entries ever shared an identifier, or one export held the same document and line twice, the run would stop with an error that names the source system, document and line (an error, not a gate result)

### AC-07 (US-06) — happy path

**Given** clean data loaded from both exports
**When** the completeness gate runs
**Then** it passes because, for each source system and transaction currency, the number of entries and the total of debits and credits in the raw data equal those in the aligned entries, and every raw entry, matched by source system, document and line, has exactly one aligned entry with the same date, signed amount and local account; the raw-side counts and totals are obtained by reading the raw files separately from the alignment, not by reusing its parsing

### AC-08 (US-06) — error

**Given** an entry is missing from the aligned entries, or its amount differs from the raw data
**When** the completeness gate runs
**Then** it fails, names the source system, the transaction currency and the difference in entry count, debit total or credit total, and names the source system, document and line of every entry that is missing or whose date, amount or local account differs (including two entries that exchanged amounts, which leave the totals unchanged), and the run ends as not successful

### AC-09 (US-03) — error

**Given** an entry whose date or amount cannot be read in the format of its source, including an ERP A entry whose debit and credit are both filled, both empty or negative, any entry of either source whose amount is zero, and any entry whose amount has more decimal places than its currency allows (2 for EUR, GBP and USD)
**When** the entries are aligned
**Then** the system does not guess a value: the entry is not accepted as aligned, so the completeness gate reports it as lost in the way AC-08 describes: the unreadable entry counts in the raw entry count but adds nothing to the raw debit or credit total, so the difference shows as a missing entry

### AC-10 (US-05) — error

**Given** an entry whose local account has no row in the account mapping for its source system
**When** the entries are aligned
**Then** the entry stays among the aligned entries with an empty group account, and the mapping gate fails and names the source system and the local account

### AC-11 (US-05) — domain invariant violation

**Given** the account mapping lists two different group accounts for the same local account of the same source system
**When** the product is run
**Then** the run stops with an error (not a gate result) that tells the Reviewer which source system and local account are ambiguous, because each local account of a source system maps to exactly one group account

### AC-12 (US-01) — authorization

**Given** a Reviewer with a fresh clone and no accounts or credentials of any kind
**When** the Reviewer runs the product
**Then** the run succeeds using only the committed files, leaves the committed exports and account mapping unchanged, and every name and amount in them is fictitious, with the README next to the committed files and the committed file names stating that the data is synthetic

### AC-13 (US-06) — cross-context

**Given** the product is declared active and the other three products are declared reserved (no gates yet), as defined in the glossary
**When** the Reviewer runs the whole repository
**Then** the failure of either gate of this product makes the overall run end as not successful, while the reserved products are listed as reserved in the run output and do not affect the result

### AC-14 (US-07) — cross-context

**Given** the next step needs an exchange rate for every transaction currency that is present
**When** the Owner reads the product documentation of the aligned entries
**Then** it lists every attribute of an aligned entry with its meaning, and the run summary lists exactly the transaction currencies that occur in the entries

## 6. Non-functional requirements

| Aspect | Target | Measurement |
|---|---|---|
| Run time of the whole-repository run command (after the one-time setup) | ≤ 30 s on the CI runner | timed step in the CI log |
| Accuracy of the completeness gate on clean data | 0 differences in entry count and in totals; amounts are held as fixed-precision decimals with 2 decimal places for EUR, GBP and USD and are never rounded (a value with more decimal places is unreadable, AC-09) | result of the completeness gate |
| Reproducibility | 100%: two generations give byte-identical files, two runs give identical entry identifiers | test comparing file hashes and identifiers |
| Readability of inputs | 100 to 250 entries per export (target ≈ 150) | test on the size of the committed files |
| Portability of product SQL | 0 constructs specific to one engine in the product SQL files, except reading the nested-record export and parsing the locale date and number formats, which live in loading code outside the SQL files (where exactly is decided in design) | review checklist now; a real run on the second platform only after step 6 and decision D1 |
| Gate scenarios | 1 passing scenario for each of the 2 gates of this step (failing scenarios belong to step 4) | automated test suite |

## 6.1 Security / privacy

- **Data classification:** public — the data is synthetic and committed to a repository meant to be read by outsiders.
- **Personal data touched:** none; all company names, people and descriptions are fictitious and marked as synthetic.
- **AuthZ/AuthN impact:** none; there are no users or permissions. The access rule is that a run needs no accounts or credentials and does not change its committed inputs (AC-12).
- **Abuse cases:**
  - Data that resembles a real company or person: every name and amount is fictitious and carries a synthetic marker.
  - A run that alters tracked input files: forbidden; the run writes only to the build area (AC-12).
  - A hand-edited input with an unreadable value: never guessed; reported as a lost entry (AC-09).
- **Security review:** N/A — demo of synthetic data, no users, no network, no secrets.

## 7. Metrics / KPIs

- **Entries lost between the raw data and the aligned entries on clean data** — baseline: n/a (the product does not exist yet), target: 0 on every run from first delivery.
- **Time from a fresh clone to a successful run (setup plus run)** — baseline: TBD; measurement plan: the Owner times it by hand on a clean environment; target: ≤ 5 minutes by 2026-11-08.
- **Deliberate source differences visibly resolved in the aligned entries** — baseline: 0 of 5 (dates, numbers, amount representation, column names, chart of accounts), target: 5 of 5 by 2026-11-10, each shown by one automated test.
- **Entries without a group account on clean data** — baseline: n/a, target: 0 on every run.

## 8. Open questions

- [ ] How must the step-3 reconciliation gate compare totals, given that balanced documents sum to zero in a signed total and would never fail? Default now: this step compares debit and credit totals separately; step 3 compares per group account or in absolute terms. — owner: Owner, due: before specifying unified-gl-ledger
- [ ] If the time budget runs out, what is cut first? Default now: roadmap steps 7 and 8 (products 2 and 3) first, as in idea-brief §6; only if that is not enough, the account mapping with its gate (replaced by one shared chart of accounts), then the nested-record export. — owner: Owner, due: before `/sdd:design unified-gl-inputs`
- [ ] Reading nested files and parsing locale formats differ between engines; where exactly does that code live, and when is it verified? Default now: in the adapter only, verified in roadmap step 6 and only if access to the second platform is confirmed (decision D1). — owner: Owner, due: before `/sdd:design unified-gl-inputs`
- [ ] What happens to a description that has no entry in the translation list, and does translating descriptions push this feature beyond size M (re-run `/sdd:classify-size`)? Default now: such a description is unreadable under AC-09, and the size stays M until the Owner decides. — owner: Owner, due: before `/sdd:design unified-gl-inputs`
- [ ] Does step 4 need a failing scenario for both gates of this step (completeness and mapping)? Default now: yes, one each. — owner: Owner, due: before specifying unified-gl-proof
