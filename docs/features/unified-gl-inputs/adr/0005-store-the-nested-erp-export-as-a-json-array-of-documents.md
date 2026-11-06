---
status: Accepted
owner: "maksym.shkilov@gmail.com"
reviewers: []
updated_at: "2026-11-05"
feature_size: "M"
ticket: ""
---

# 0005 — Store the nested ERP export as a JSON array of documents

- **Status:** Accepted
- **Date:** 2026-11-05
- **Deciders:** Owner + Architect (design session)

## Context

The spec fixes that the second export is a nested-record file and the first a flat tabular text file, but not the file format of the nested one. The generator writes it, both adapters read it (ADR-0001), the Reviewer reads it by eye (AC-03), and the raw layer must keep it nested.

## Decision drivers

- AC-03: for the nested export the raw data stays nested.
- Readability: the Reviewer opens the raw file first (spec §1, idea-brief §2).
- Portability: DuckDB and Spark SQL must both read it without extensions (spec §6, ADR-0004 of the repository).
- Reproducibility: the generator must write byte-identical files (spec §6).

## Considered options

1. **JSON file with an array of document objects** — each document has header fields and a nested `lines` array; pretty-printed.
2. **JSON Lines** — one complete document per line, each with a nested `lines` array.

## Decision outcome

**Chosen:** Option 1. A pretty-printed document with its lines nested under it is the form a Reviewer reads most easily and the closest to «nested records». DuckDB reads it with `read_json`; Spark needs the `multiLine` option, which is one setting in the Databricks adapter. Option 2 reads on Spark without options and diffs better in git, but a full document on one line is hard to read by eye.

## Consequences

**Positive**
- The raw file can be read and checked by eye; the nested shape survives into `raw`.
- The generator writes it with the standard `json` module with fixed key order and indentation.

**Negative**
- The whole file is read at once, which is irrelevant at 100 to 250 entries per export.
- Git diffs of a regenerated file are less line-oriented than with JSON Lines.

**Neutral**
- The exact field names and the language of ERP B are fixed by the `data-model` stage; this decision fixes only the container format.

## Links

- Spec: [[../spec.md]] AC-03, AC-05, §6
- SAD: [[../sad.md]] §8
- Related ADR: [[0001-expose-typed-flat-views-from-per-engine-adapters]]
