"""Seeded generator for the synthetic Unified GL inputs (all names and amounts are fictitious).

Run: python products/unified_gl/data/generate.py
Writes five files next to this script and prints the entry count of each export.
Same seed -> byte-identical files: amounts come from integer cents, no timestamps,
fixed row and key order, LF line endings.
"""

import hashlib
import json
import random
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

SEED = 20260101
DATA_DIR = Path(__file__).resolve().parent
Q_START, Q_END = date(2026, 1, 1), date(2026, 3, 31)
RATES_TO_USD = {"EUR": Decimal("1.0850"), "GBP": Decimal("1.2700"), "USD": Decimal(1)}

# local account -> group account, per source system. 4710 exists in both charts on purpose
# and maps to different group accounts (AC-04).
CHART = {
    "ERP_A": {
        "1200": "1000", "1400": "1100", "1600": "1500", "1800": "2000", "2900": "3000",
        "8000": "4000", "3400": "5000", "4100": "6000", "4210": "6100", "4660": "6200",
        "4710": "6300", "4800": "7000",
    },
    "ERP_B": {
        "1010": "1000", "1210": "1100", "1310": "1500", "2010": "2000", "3010": "3000",
        "4010": "4000", "5010": "5000", "6010": "6000", "6020": "6100", "6030": "6200",
        "4710": "7000", "6040": "6300",
    },
}
# Account roles for building balanced documents.
EXPENSE = {"ERP_A": ["3400", "4100", "4210", "4660", "4710", "4800"],
           "ERP_B": ["5010", "6010", "6020", "6030", "4710", "6040"]}
SETTLE = {"ERP_A": ["1200", "1800"], "ERP_B": ["1010", "2010"]}
REVENUE = {"ERP_A": ["8000"], "ERP_B": ["4010"]}
RECEIVABLE = {"ERP_A": ["1400", "1200"], "ERP_B": ["1210", "1010"]}

# German description -> English (ERP A). ERP B writes English already.
DE_TO_EN = {
    "Büromaterial Einkauf": "Office supplies purchase",
    "Miete Bürogebäude": "Office building rent",
    "Reisekosten Außendienst": "Field sales travel costs",
    "Eingangsrechnung Lieferant": "Supplier invoice received",
    "Ausgangsrechnung Kunde": "Customer invoice issued",
    "Bankgebühren Quartal": "Bank fees for the quarter",
    "Gehälter Monatslauf": "Monthly payroll run",
    "Softwarelizenz Jahresgebühr": "Annual software license fee",
    "Marketingkampagne Frühjahr": "Spring marketing campaign",
    "Zahlung Kunde": "Customer payment",
}
# Deliberately without a translation row: the exceptions report is non-empty on clean data.
UNTRANSLATED_DE = ["Bewirtung Kundentermin", "Wartungsvertrag Aufzug",
                   "Sonderabschreibung Fuhrpark", "Rückstellung Rechtsstreit"]
EN_MEMOS = ["Office supplies", "Warehouse rent", "Sales trip expenses", "Vendor invoice",
            "Client invoice", "Bank charges", "Payroll run", "Software subscription",
            "Advertising campaign", "Client payment"]

DOCS_PER_SYSTEM = 60


def _entry_id(system: str, document: str, line: int) -> str:
    return hashlib.md5(f"{system}|{document}|{line}".encode()).hexdigest()


def _build_documents(rng: random.Random, system: str, descriptions: list[str],
                     currencies: list[str], untranslated: list[str]) -> list[dict]:
    """Balanced documents: one currency, one date, signed cents summing to zero."""
    docs = []
    for n in range(1, DOCS_PER_SYSTEM + 1):
        day = Q_START + timedelta(days=rng.randrange((Q_END - Q_START).days + 1))
        currency = rng.choice(currencies)
        description = untranslated[(n // 14) - 1] if n % 14 == 0 and n // 14 <= len(untranslated) \
            else rng.choice(descriptions)
        revenue = rng.random() < 0.3
        split = rng.choice([1, 1, 2])
        main_side = REVENUE[system] if revenue else EXPENSE[system]
        other_side = RECEIVABLE[system] if revenue else SETTLE[system]
        parts = [rng.randrange(10_000, 2_500_000) for _ in range(split)]
        lines = []
        for cents in parts:  # revenue: credit revenue, debit receivable; expense: the reverse
            lines.append((rng.choice(main_side), -cents if revenue else cents))
        lines.append((rng.choice(other_side), sum(parts) if revenue else -sum(parts)))
        docs.append({"n": n, "date": day, "currency": currency, "description": description,
                     "lines": lines})
    return docs


def _de_amount(cents: int) -> str:
    whole, frac = divmod(cents, 100)
    return f"{whole:,}".replace(",", ".") + f",{frac:02d}"


def _us_amount(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents), 100)
    return f"{sign}{whole:,}.{frac:02d}"


def generate(out_dir: Path = DATA_DIR) -> list[dict]:
    """Write the five input files into out_dir; return the expected aligned entries."""
    rng = random.Random(SEED)
    out_dir.mkdir(parents=True, exist_ok=True)
    de_texts = list(DE_TO_EN)
    docs_a = _build_documents(rng, "ERP_A", de_texts, ["EUR", "EUR", "EUR", "GBP"],
                              UNTRANSLATED_DE)
    docs_b = _build_documents(rng, "ERP_B", EN_MEMOS, ["USD", "USD", "USD", "USD", "GBP"], [])

    expected: list[dict] = []

    def add(system, document, line, day, cents, currency, account, description, original):
        expected.append({
            "entry_id": _entry_id(system, document, line), "source_system": system,
            "source_document": document, "source_line": line, "entry_date": day,
            "signed_amount": Decimal(cents) / 100, "transaction_currency": currency,
            "local_account": account, "group_account": CHART[system][account],
            "description": description, "original_description": original,
        })

    a_rows = ["belegnummer;zeile;buchungsdatum;konto;sollbetrag;habenbetrag;waehrung;buchungstext"]
    for doc in docs_a:
        number = f"BA-2026-{doc['n']:04d}"
        for line, (account, cents) in enumerate(doc["lines"], start=1):
            debit = _de_amount(cents) if cents > 0 else ""
            credit = _de_amount(-cents) if cents < 0 else ""
            a_rows.append(";".join([number, f"{line:02d}", doc["date"].strftime("%d.%m.%Y"),
                                    account, debit, credit, doc["currency"],
                                    doc["description"]]))
            add("ERP_A", number, line, doc["date"], cents, doc["currency"], account,
                DE_TO_EN.get(doc["description"], doc["description"]), doc["description"])

    b_docs = []
    for doc in docs_b:
        number = f"B{doc['n']:06d}"
        b_lines = []
        for line, (account, cents) in enumerate(doc["lines"], start=1):
            b_lines.append({"line_no": str(line), "account": account,
                            "amount": _us_amount(cents), "memo": doc["description"]})
            add("ERP_B", number, line, doc["date"], cents, doc["currency"], account,
                doc["description"], doc["description"])
        b_docs.append({"doc_id": number, "posting_date": doc["date"].strftime("%m/%d/%Y"),
                       "currency": doc["currency"], "lines": b_lines})

    mapping = ["source_system,local_account,group_account"]
    for system, chart in CHART.items():
        mapping += [f"{system},{local},{group}" for local, group in chart.items()]

    translation = ["source_system,original_description,common_description"]
    translation += [f"ERP_A,{de},{en}" for de, en in DE_TO_EN.items()]
    translation += [f"ERP_B,{memo},{memo}" for memo in EN_MEMOS]

    rates = ["date,currency,rate_to_usd"]
    for offset in range((Q_END - Q_START).days + 1):
        day = Q_START + timedelta(days=offset)
        for currency, rate in RATES_TO_USD.items():
            drift = Decimal(0) if currency == "USD" else Decimal((offset * 7) % 25) / 10_000
            rates.append(f"{day.isoformat()},{currency},{rate + drift}")

    files = {
        "erp_a_export_synthetic.csv": "\n".join(a_rows) + "\n",
        "erp_b_export_synthetic.json": json.dumps(b_docs, indent=2, ensure_ascii=False) + "\n",
        "account_mapping_synthetic.csv": "\n".join(mapping) + "\n",
        "description_translation_synthetic.csv": "\n".join(translation) + "\n",
        "rates_synthetic.csv": "\n".join(rates) + "\n",
    }
    for name, text in files.items():
        with (out_dir / name).open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)

    return sorted(expected, key=lambda e: (e["source_system"], e["source_document"],
                                           e["source_line"]))


def main(out_dir: Path = DATA_DIR) -> int:
    try:
        entries = generate(out_dir)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    for name, system in (("erp_a_export_synthetic.csv", "ERP_A"),
                         ("erp_b_export_synthetic.json", "ERP_B")):
        print(f"{name}: {sum(e['source_system'] == system for e in entries)} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
