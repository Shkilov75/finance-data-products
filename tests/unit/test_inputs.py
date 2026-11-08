"""Checks on the committed synthetic inputs, with plain Python (no DuckDB).

``problems(folder)`` returns a list of findings; the committed folder must give none, and
each corrupted copy must give some, so the checks cannot pass by asserting nothing.
"""

import csv
import hashlib
import importlib.util
import json
import shutil
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from fdp_core.config import repo_root

DATA = repo_root() / "products/unified_gl/data"
GENERATOR = DATA / "generate.py"
INPUTS = [
    "erp_a_export_synthetic.csv",
    "erp_b_export_synthetic.json",
    "account_mapping_synthetic.csv",
    "description_translation_synthetic.csv",
    "rates_synthetic.csv",
]
Q_START, Q_END = date(2026, 1, 1), date(2026, 3, 31)


def de_number(text: str) -> Decimal:
    return Decimal(text.replace(".", "").replace(",", "."))


def us_number(text: str) -> Decimal:
    return Decimal(text.replace(",", ""))


def read_documents(folder):
    """Return {(system, document): {'date', 'currency', 'amounts': [signed Decimal], 'keys'}}."""
    docs = defaultdict(lambda: {"date": None, "currency": set(), "amounts": [], "keys": []})
    with (folder / "erp_a_export_synthetic.csv").open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            doc = docs[("ERP_A", row["belegnummer"])]
            doc["date"] = datetime.strptime(row["buchungsdatum"], "%d.%m.%Y").date()
            doc["currency"].add(row["waehrung"])
            debit, credit = row["sollbetrag"], row["habenbetrag"]
            doc["amounts"].append(de_number(debit) if debit else -de_number(credit))
            doc["keys"].append(row["zeile"])
    for item in json.loads((folder / "erp_b_export_synthetic.json").read_text(encoding="utf-8")):
        doc = docs[("ERP_B", item["doc_id"])]
        doc["date"] = datetime.strptime(item["posting_date"], "%m/%d/%Y").date()
        doc["currency"].add(item["currency"])
        for line in item["lines"]:
            doc["amounts"].append(us_number(line["amount"]))
            doc["keys"].append(line["line_no"])
    return docs


def problems(folder) -> list[str]:
    found = []
    for name in INPUTS:
        if "synthetic" not in name or not (folder / name).is_file():
            found.append(f"missing or badly named input {name}")
    if found:
        return found
    docs = read_documents(folder)
    for system in ("ERP_A", "ERP_B"):
        entries = sum(len(d["keys"]) for (s, _), d in docs.items() if s == system)
        if not 100 <= entries <= 250:
            found.append(f"{system} holds {entries} entries")
    currencies = set()
    for (system, number), doc in docs.items():
        currencies |= doc["currency"]
        if not number or any(not k for k in doc["keys"]):
            found.append(f"{system} {number}: document or line missing")
        if not Q_START <= doc["date"] <= Q_END:
            found.append(f"{system} {number}: date {doc['date']} outside the first quarter")
        if len(doc["currency"]) != 1:
            found.append(f"{system} {number}: currencies {sorted(doc['currency'])}")
        if sum(doc["amounts"]) != 0:
            found.append(f"{system} {number}: does not balance")
    if not {"EUR", "GBP", "USD"} <= currencies:
        found.append(f"currencies used: {sorted(currencies)}")
    with (folder / "rates_synthetic.csv").open(encoding="utf-8", newline="") as fh:
        rates = list(csv.DictReader(fh))
    seen = defaultdict(int)
    for row in rates:
        seen[(row["date"], row["currency"])] += 1
        if row["currency"] == "USD" and Decimal(row["rate_to_usd"]) != 1:
            found.append(f"USD rate on {row['date']} is {row['rate_to_usd']}")
    days = (Q_END - Q_START).days + 1
    for offset in range(days):
        day = (Q_START + timedelta(days=offset)).isoformat()
        for currency in currencies:
            if seen[(day, currency)] != 1:
                found.append(f"rate rows for {currency} on {day}: {seen[(day, currency)]}")
    return found


def load_generator():
    spec = importlib.util.spec_from_file_location("unified_gl_generate_t4", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_committed_inputs_pass_every_check():
    assert problems(DATA) == []


def test_regeneration_is_byte_identical_to_committed_files(tmp_path):
    gen = load_generator()
    first, second = tmp_path / "one", tmp_path / "two"
    gen.generate(first)
    gen.generate(second)
    for name in INPUTS:
        assert sha(first / name) == sha(second / name) == sha(DATA / name), name


def test_all_input_names_say_synthetic():
    assert all("synthetic" in n for n in INPUTS)
    assert {p.name for p in DATA.iterdir() if p.suffix in {".csv", ".json"}} == set(INPUTS)


@pytest.fixture
def copy(tmp_path):
    target = tmp_path / "data"
    shutil.copytree(DATA, target)
    return target


def edit(path, old, new, count=1):
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, count), encoding="utf-8")


def change_first_a_row(folder, column, value):
    path = folder / "erp_a_export_synthetic.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    cells = lines[1].split(";")
    cells[column] = value
    lines[1] = ";".join(cells)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_detects_unbalanced_document(copy):
    row = (copy / "erp_a_export_synthetic.csv").read_text(encoding="utf-8").splitlines()[1]
    column = 4 if row.split(";")[4] else 5  # the filled side of the first entry
    change_first_a_row(copy, column, "9.999.999,99")
    assert any("does not balance" in p for p in problems(copy))


def test_detects_date_outside_first_quarter(copy):
    path = copy / "erp_b_export_synthetic.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data[0]["posting_date"] = "07/01/2026"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert any("outside the first quarter" in p for p in problems(copy))


def test_detects_two_currencies_in_one_document(copy):
    row = (copy / "erp_a_export_synthetic.csv").read_text(encoding="utf-8").splitlines()[1]
    change_first_a_row(copy, 6, "USD" if row.split(";")[6] != "USD" else "EUR")
    assert any("currencies" in p for p in problems(copy))


def test_detects_missing_rate_day(copy):
    path = copy / "rates_synthetic.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    del lines[5]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert any("rate rows" in p for p in problems(copy))


def test_detects_duplicate_rate_row(copy):
    path = copy / "rates_synthetic.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    lines.append(lines[5])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert any("rate rows" in p for p in problems(copy))


def test_detects_usd_rate_not_one(copy):
    edit(copy / "rates_synthetic.csv", ",USD,1", ",USD,2")
    assert any("USD rate" in p for p in problems(copy))


def test_detects_too_few_entries(copy):
    path = copy / "erp_a_export_synthetic.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(lines[:40]) + "\n", encoding="utf-8")
    assert any("holds" in p for p in problems(copy))


def test_detects_missing_line_number(copy):
    change_first_a_row(copy, 1, "")
    assert any("document or line missing" in p for p in problems(copy))


def test_detects_missing_currency_gbp(copy):
    path = copy / "erp_a_export_synthetic.csv"
    path.write_text(path.read_text(encoding="utf-8").replace(";GBP;", ";EUR;"), encoding="utf-8")
    data = json.loads((copy / "erp_b_export_synthetic.json").read_text(encoding="utf-8"))
    for item in data:
        item["currency"] = "USD" if item["currency"] == "GBP" else item["currency"]
    (copy / "erp_b_export_synthetic.json").write_text(json.dumps(data), encoding="utf-8")
    assert any("currencies used" in p for p in problems(copy))


def test_detects_badly_named_input(copy):
    (copy / "rates_synthetic.csv").rename(copy / "rates.csv")
    assert any("badly named" in p for p in problems(copy))
