---
status: Living
updated_at: "2026-11-05"
---

# Domain Context — unified-gl-inputs

<!--
CONTEXT.md is the domain glossary — not a spec and not a scratch pad. NO implementation
detail here (no datastore/broker/framework names, no API contracts) — only domain words
and the boundaries between them. Implementation choices live in the SAD and ADRs; behaviour
lives in spec.md.

Terms get fixed inline, the moment they surface in an interview / spec / review — never
batched «I'll consolidate later». Empty H2 → prune before commit; keep only the sections
that carry real content. ## Glossary

- Aligned entry set — the table `staging.ledger_entry`: one row per accepted ledger entry of either source system, in transaction currency, with signed amount, group account and entry identifier. An entry is accepted when its date and amount can be read in the format of its source; an unreadable entry is not accepted and is reported as lost by the completeness gate. The group account may be empty (NULL) when no mapping exists, which is what the mapping gate catches. NOT the raw data: raw keeps each export as it arrived.
- Completeness gate — gate that compares entry count, debit total and credit total, and every entry, between the raw data and the aligned entry set. NOT the mapping gate, which checks only that each entry has a group account.
- Control view — view in the `raw` schema that re-reads the raw tables with a separate parse and gives the raw side of the completeness gate. NOT a typed view, which feeds the alignment.
- Entry identifier — deterministic md5 hash of source system, document and line, unique across both source systems; it is the key of the aligned entry set, and the unique-entry-id invariant check enforces its uniqueness (AC-06). NOT a random UUID.
- Exceptions report — `exceptions_report.csv` listing untranslated descriptions, which keep their original text in the aligned entry set. NOT an error: the entry stays aligned and the run still succeeds.
- Mapping gate — gate that fails when an aligned entry has no group account, naming its source system and local account. NOT the completeness gate, and NOT the ambiguous-mapping invariant check, which stops the run instead of failing a gate.
- Typed view — adapter view with fixed names and column types that the neutral SQL starts from. NOT a control view, which re-reads the raw data for the gate.
