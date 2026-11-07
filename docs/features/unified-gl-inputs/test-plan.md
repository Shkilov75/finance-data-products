---
status: Draft
owner: "maksym.shkilov@gmail.com"
reviewers: ["maksym.shkilov@gmail.com"]
updated_at: "2026-11-06"
feature_size: "M"
---

# Test plan — unified-gl-inputs

Two synthetic ERP exports are generated reproducibly, loaded, aligned into one entry set in transaction currency, and guarded by a completeness gate and a mapping gate; every acceptance criterion of `spec.md` §5 below maps to at least one named test.

## Levels

The surface is a command line (`target_surfaces: [cli]`), so the UI tiers (component, visual-regression, e2e-through-UI) do not apply.

| Level | Scope | Strategy (generic — no tool names) |
|---|---|---|
| Unit | Pure logic with no database: the entry-identifier derivation, the generator's value rules, file-level checks of the committed inputs (size, dates, balance, daily rates, hashes, synthetic markers), a static scan of the product SQL files. | In-memory; reads only committed files; no database. |
| Integration | The SQL of the product (typed views, control views, aligned entry set, invariant checks, both gates, summary and exceptions queries) against the real embedded analytical engine. | A fresh throwaway database per test (in memory or in a temporary folder), loaded from small hand-made fixtures; never a mocked store. |
| Contract | The boundaries both sides agree on: the typed-view names and column types the neutral SQL starts from (adapter ↔ neutral SQL), and the command-line output and exit codes in `contracts/cli.md`; the README attribute list against `data-model.md`. | Compare the real output and the real view definitions with the agreed contract documents; no hand-rolled stubs. |
| E2E | The whole single-command run on the committed clean data. | The real entry point, with the build area redirected to a temporary folder, against the committed inputs. |
| Load | Only the one numeric NFR (run time). | The load/timing tool already in the repo, or e.g. k6 or Locust; a plain timed loop is enough for a command line. |

## AC coverage

Levels in the third column are the ones the owner confirmed on 2026-11-06 for each group of criteria. «Known values» means the list of expected aligned entries that the generator returns next to the files; comparing the aligned entry set with it is the only check that catches a misreading shared by both parsers (SAD §10 QG-1).

| AC (spec.md §5) | Test name (intent-based) | Level | Expected outcome |
|---|---|---|---|
| AC-01 happy path | `single run prints per-source per-currency summary and both gates passed` | e2e | Run ends successfully; for each source system and currency the summary shows entry count, debit total and credit total; the text says both gates passed |
| AC-01 happy path | `summary counts and totals equal known values` | integration | Summary query on a small fixture returns the counts and the separate debit and credit totals (not a signed total) |
| AC-01 happy path | `summary shows exceptions-report count next to the report name, zero included` | e2e | The line with the report name carries a number; the number equals the record count of the report file |
| AC-01 happy path | `run output follows the agreed order and exit code` | contract | Output sections and exit code 0 match `contracts/cli.md` |
| AC-02 happy path | `five source differences are resolved in the aligned entries` (five tests: dates, numbers, amount representation, column names, charts of accounts) | integration | One test per difference: each source's raw form becomes the common form (real calendar date, numeric amount, same attribute names, group account) |
| AC-02 happy path | `aligned entries equal the generator's known values` | e2e | Every aligned entry from the committed data equals its known value (identifier, signed amount, group account, common description) |
| AC-02 happy path | `debit is positive and credit is negative in both sources` | integration | ERP A filled debit cell → positive, filled credit cell → negative; ERP B positive → debit, negative → credit; a cell holding zero counts as filled |
| AC-02 happy path | `description is translated only on exact whole-text match` | integration | An exact match is replaced by the English text; a differing case or a partial match keeps the original text |
| AC-02 happy path | `untranslated description stays aligned and is written to exceptions report` | integration | The entry stays in the aligned set with its original text; one record per such entry with the four named columns; the run still succeeds |
| AC-02 happy path | `exceptions report on committed data lists the untranslated entries` | e2e | The report file exists after the run and holds the entries that the generator left without a translation |
| AC-02 happy path | `typed views have the agreed names and column types` | contract | Typed-view column names and types equal the definition in `data-model.md` (the boundary between the adapter and the neutral SQL) |
| AC-03 happy path | `aligned entry traces to its raw record with the same date, amount and account` | integration | For fixture entries from both sources, the raw record found by source system, document and line shows the same date, amount and local account once read in its source format; ERP B record stays nested |
| AC-03 happy path | `every committed entry traces to its raw record` | e2e | For every aligned entry of the committed data, source system, document and line find exactly one raw record with equal date, amount and account |
| AC-04 happy path | `entry carries the group account of its source's mapping` | integration | The aligned entry has the group account assigned to its local account in its own source system |
| AC-04 happy path | `same local account code maps differently per source` | integration | One account code present in both charts gets two different group accounts, each applied only to its own source |
| AC-05 happy path | `second generation is byte-identical to the first` | unit | File hashes of two fresh generations are equal, and equal to the committed files |
| AC-05 happy path | `each export holds 100 to 250 entries, dated January to March 2026` | unit | Entry counts inside the range; every date inside the first quarter of 2026 |
| AC-05 happy path | `every entry has explicit document and line number` | unit | No empty document or line value in either export |
| AC-05 happy path | `exports use at least EUR, GBP and USD` | unit | The set of transaction currencies of both exports contains all three |
| AC-05 happy path | `every document is in one currency and balances` | unit | For each document: one currency; total of debits equals total of credits |
| AC-05 happy path | `rate file has one rate per currency per day, USD is 1` | unit | Exactly one row per occurring currency per calendar day from 2026-01-01 to 2026-03-31; USD rate equals 1 |
| AC-06 domain invariant | `entry identifier is derived from source, document and line` | unit | Same three values give the same identifier; document taken as written with trimmed spaces; changing any value changes the identifier |
| AC-06 domain invariant | `line «01» and «1» give the same identifier` | unit | Identifiers equal |
| AC-06 domain invariant | `two entries of one document with equal date, account and amount keep different identifiers` | integration | Both entries stay in the aligned set with distinct identifiers |
| AC-06 domain invariant | `identifiers are unique across both sources and equal in two runs` | integration | No identifier repeats; the list of identifiers of run 1 equals that of run 2 |
| AC-06 domain invariant | `identifiers are equal in two runs on committed data` | e2e | Two complete runs give the identical identifier list |
| AC-07 happy path | `completeness gate passes on clean data` | integration | Gate returns no rows: counts and totals per source and currency equal; every raw entry has exactly one aligned entry with the same date, signed amount and account |
| AC-07 happy path | `completeness gate passes on the committed data` | e2e | Run ends with exit code 0 and the gate reported as passed |
| AC-07 happy path | `raw side is read independently of the alignment` | integration | The control view gives the same figures as an independent computation from the fixture's known values; it does not use the typed views |
| AC-07 happy path | `records loaded equal records in each file` | integration | For each input file, the number of records in the file equals the number loaded into the raw table (a record lost on load is caught here) |
| AC-07 happy path | `mapping gate passes on clean data` | integration | Mapping gate returns no rows when every entry has a group account |
| AC-13 cross-context | `failure of either product gate fails the whole run` | integration | With a fixture product whose gate returns a row, the run ends not successful (exit code 1); the same for each of the two gates |
| AC-13 cross-context | `reserved products are listed and do not affect the result` | e2e | The output lists the three other products as reserved; the exit code is unchanged by them |
| AC-13 cross-context | `gate failure uses the agreed exit code and output` | contract | A failed gate gives exit code 1 and the failing-gate layout of `contracts/cli.md` |
| AC-14 cross-context | `README lists every aligned entry attribute with its meaning` | contract | Every column of the aligned entry set in `data-model.md` appears in the README with a description (at least identifier, source system, document, line, date, signed amount, transaction currency, local account, group account, description, original description) |
| AC-14 cross-context | `summary lists exactly the currencies in the entries` | e2e | The set of currencies in the run summary equals the set in the aligned entry set |
| AC-14 cross-context | `summary lists a currency that occurs and no other` | integration | A fixture with only EUR and GBP entries gives exactly those two currencies in the summary |

## Edge cases / error paths

Every error, authorization and domain-invariant criterion has its own dedicated rows here; none is folded into a happy path. Failing-gate scenarios run on small hand-made fixtures; the corrupted-data scenarios of roadmap step 4 are not built here.

| AC | Case | Level | Expected outcome |
|---|---|---|---|
| AC-08 error | `entry missing from the aligned entries fails the completeness gate` | integration | Gate fails; names source system, currency and the difference in entry count; names source system, document and line of the missing entry |
| AC-08 error | `changed amount fails the completeness gate` | integration | Gate fails; names the debit or credit total difference and the entry whose amount differs |
| AC-08 error | `changed date or local account fails the completeness gate` | integration | Gate fails; names source system, document and line of the entry that differs |
| AC-08 error | `two entries that exchanged amounts are still caught` | integration | Totals are unchanged, yet the gate fails and names both entries |
| AC-08 error | `gate result lists both kinds of difference` | integration | One gate result shows count/total differences per source and currency and the individual entries |
| AC-08 error | `completeness failure ends the run as not successful` | contract | Exit code 1 with the failing-gate layout of `contracts/cli.md` |
| AC-09 error | `ERP A entry with debit and credit both filled is not accepted` | integration | Not in the aligned set; counted in the raw entry count; adds nothing to raw debit or credit totals; the completeness gate fails and names it |
| AC-09 error | `ERP A entry with debit and credit both empty is not accepted` | integration | Same outcome |
| AC-09 error | `ERP A entry with a negative debit or credit is not accepted` | integration | Same outcome |
| AC-09 error | `entry with a zero amount is not accepted (either source)` | integration | Same outcome for ERP A and for ERP B |
| AC-09 error | `amount with more decimal places than the currency allows is not accepted` | integration | Same outcome for an amount with three decimals in EUR, GBP and USD |
| AC-09 error | `unreadable date is not accepted and not guessed` | integration | Same outcome for a date in the wrong format, an impossible calendar date and a text that is not a date |
| AC-09 error | `unreadable amount is not accepted and not guessed` | integration | Same outcome for a text that is not a number |
| AC-09 error | `unreadable entry does not reach the raw totals` | integration | The independent raw-side reading applies each rule by itself; the difference shown by the gate equals the unreadable entry |
| AC-10 error | `entry without a mapping row stays aligned with an empty group account` | integration | The entry is in the aligned set; its group account is empty |
| AC-10 error | `mapping gate fails and names source system and local account` | integration | Gate returns a row naming the source system and the local account |
| AC-10 error | `local account mapped only in the other source still fails` | integration | A code present in the mapping for ERP A only fails for the ERP B entry that uses it |
| AC-10 error | `mapping failure ends the run as not successful` | contract | Exit code 1 with the failing-gate layout of `contracts/cli.md` |
| AC-06 domain invariant | `same source, document and line twice in one export stops the run` | integration | Run stops with an error (not a gate result) naming source system, document and line |
| AC-06 domain invariant | `duplicate that is also unreadable still stops the run` | integration | The raw records are checked before any readability rule, so the run stops with the same error |
| AC-06 domain invariant | `colliding entry identifiers stop the run` | integration | Run stops with an error naming source system, document and line |
| AC-06 domain invariant | `invariant stop uses the agreed exit code and message` | contract | Exit code 2; first line `invariant violation:` per `contracts/cli.md`; no report file left from this or an earlier run |
| AC-11 domain invariant | `same local account twice with different group accounts stops the run` | integration | Run stops with an error naming source system and local account |
| AC-11 domain invariant | `same local account twice with the same group account stops the run` | integration | Same outcome |
| AC-11 domain invariant | `ambiguous mapping stops the run before the gates` | contract | Exit code 2 and the stderr layout of `contracts/cli.md`; gates are not executed |
| AC-12 authorization | `run needs no accounts, network or credentials` | e2e | With the network-related and credential-related environment emptied, the run on a fresh copy of the repository succeeds |
| AC-12 authorization | `run leaves every committed input file unchanged` | e2e | Hashes of the five input files are equal before and after the run; the run wrote only inside the build area |
| AC-12 authorization | `names and amounts are fictitious and files are marked synthetic` | unit | The name of each of the five input files contains the word «synthetic»; the README next to them states that the data is synthetic |

Further boundary cases:

- Empty exceptions report → expected: the file exists with only its header (integration, fixture where every description has a translation).
- Description with leading or trailing spaces or a different case than the translation list → expected: not translated, listed in the report.
- Line number written as «01» in ERP A and as «1» in ERP B for the same document text → expected: two different entries, since the source system is part of the identifier.
- Product SQL files contain engine-specific constructs or file-reading code (spec §6 portability) → expected: a static scan of the neutral SQL files finds none (unit); engine-specific parts live only in the adapter folder.

## Test data

- Seed strategy: small hand-made fixtures in the shape of the five raw tables in `data-model.md` (a few entries per source and currency; one fixture per case above), plus the committed clean data produced by the generator from its fixed seed. The generator's «known values» list is the expected result for the end-to-end comparison.
- Integration dependency: the real embedded analytical engine, in a fresh throwaway database for each test; no mocked store, no shared database file.
- Cleanup boundary: per test. Each test creates its own database in a temporary folder and deletes it afterwards; the end-to-end tests redirect the build area to a temporary folder and never write into the repository. Committed input files are only read; a test that hashes them runs before and after.
- Corrupting data for the step-4 demo (`corrupt(...)`) is not built here; fixtures for AC-08 to AC-11 are written by hand and kept small.

## NFR validation (load)

Only one NFR in `spec.md` §6 carries a number that a timing test can check; the other numeric targets (0 differences in count and totals, 100 to 250 entries per export, 100% reproducibility) are exact checks and are covered in the AC coverage table (AC-07, AC-05, AC-06).

- NFR: whole-repository run ≤ 30 s on the CI runner → scenario: one run at a time on the committed data, 5 consecutive runs (about 2.5 minutes at most), assert the wall time of every run ≤ 30 s; the load/timing tool already in the repo, or e.g. k6 or Locust (a plain timed loop is enough). The same threshold is also read from the timed step in the CI log.

## CI placement

- On every PR: unit (inputs, identifier, static SQL scan), integration (SQL on small fixtures) and contract (typed views, command-line output, README attributes) — all fast, no network.
- On every PR as well: the end-to-end run on the committed data, since it takes well under 30 s and is the only check that catches an error shared by both parsers; the timing loop runs on the same job.
- On schedule / pre-release: nothing extra now; the second-platform check belongs to roadmap step 6 and the failing-gate demo to step 4.
