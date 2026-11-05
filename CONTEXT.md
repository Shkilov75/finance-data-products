---
status: Living
updated_at: "2026-11-04"
---

# Domain Context — finance-data-products

## Glossary

- Account mapping — the reference list that says which group account each local account of each source system belongs to. NOT a currency conversion: it changes the account, never the amount.
- Active product — a product with SQL, gates and data that the whole-repository run executes, and whose gate failure makes the run unsuccessful. NOT a reserved product: it is actually built.
- ERP export — a file that one source system produced from its books, in its own format and conventions. NOT the unified ledger: it is one source's raw view, unchanged.
- Gate — a quality check on the data that passes when it finds no violating rows and fails otherwise. NOT an error or crash: a failed gate is a normal reported result.
- Group account — an account in the single common chart that all source systems are mapped to. NOT a local account: it is what the unified ledger reports on.
- Layer — one stage of the data build: raw (source files as they arrived), staging (cleaned and aligned to one shape), mart (published result). NOT a separate product: all layers of one product are rebuilt together.
- Ledger entry — one posting line of a general ledger: a date, an account, an amount in one currency, and a description. NOT a whole journal document: several entries can belong to one document.
- Local account — an account code as one source system uses it in its own chart of accounts. NOT a group account: the same code can mean different things in two source systems.
- Owner — the repo author who builds the products and presents them in the interview. NOT an operator of a production system: there is no support or on-call.
- Reserved product — a product declared in the repository with no gates yet; the whole-repository run only lists it as reserved and it never affects the result. NOT a deleted or abandoned product: it is planned.
- Reviewer — a hiring manager or interviewer who reads the repo before or during an interview and may clone and run it. NOT a business user of the finance data: nobody consumes the numbers.
- Source system — one of the ERP systems whose export the product ingests (here ERP A and ERP B). NOT a database or server of this repo.
- Transaction currency — the currency in which a ledger entry was originally posted. NOT the reporting currency (USD): converting to USD happens later.
