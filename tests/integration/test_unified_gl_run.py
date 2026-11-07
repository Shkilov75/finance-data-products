"""End-to-end checks on a real `fdp run` of unified_gl with the committed synthetic inputs."""

import csv
import importlib.util
import json
import tempfile
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from fdp_core.config import repo_root

ROOT = repo_root()
DATA = ROOT / "products/unified_gl/data"
COLUMNS = ["entry_id", "source_system", "source_document", "source_line", "entry_date",
           "signed_amount", "transaction_currency", "local_account", "group_account",
           "description", "original_description"]
INPUTS = ["erp_a_export_synthetic.csv", "erp_b_export_synthetic.json",
          "account_mapping_synthetic.csv", "description_translation_synthetic.csv",
          "rates_synthetic.csv"]


def de_number(text):
    return Decimal(text.replace(".", "").replace(",", "."))


def us_number(text):
    return Decimal(text.replace(",", ""))


def raw_records():
    """Independent plain-Python reading of both exports: {(system, document, line): (date, amount, account)}."""
    records = {}
    with (DATA / "erp_a_export_synthetic.csv").open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            amount = (de_number(row["sollbetrag"]) if row["sollbetrag"]
                      else -de_number(row["habenbetrag"]))
            records[("ERP_A", row["belegnummer"], int(row["zeile"]))] = (
                datetime.strptime(row["buchungsdatum"], "%d.%m.%Y").date(), amount, row["konto"])
    for doc in json.loads((DATA / "erp_b_export_synthetic.json").read_text(encoding="utf-8")):
        day = datetime.strptime(doc["posting_date"], "%m/%d/%Y").date()
        for line in doc["lines"]:
            records[("ERP_B", doc["doc_id"], int(line["line_no"]))] = (
                day, us_number(line["amount"]), line["account"])
    return records


def entries(db):
    return db.execute(f"SELECT {', '.join(COLUMNS)} FROM staging.ledger_entry "
                      "ORDER BY source_system, source_document, source_line").fetchall()


# ---- the five deliberate source differences --------------------------------------------------

def test_difference_1_dates_in_two_formats_become_the_same_date_type(db):
    assert db.execute("SELECT typeof(entry_date) FROM staging.ledger_entry LIMIT 1").fetchone() == ("DATE",)
    raw = raw_records()
    for system in ("ERP_A", "ERP_B"):
        got = {(r[1], r[2], r[3]): r[4] for r in entries(db) if r[1] == system}
        assert got and all(raw[k][0] == v for k, v in got.items())


def test_difference_2_numbers_in_two_formats_become_exact_decimals(db):
    raw = raw_records()
    for system in ("ERP_A", "ERP_B"):
        got = [r for r in entries(db) if r[1] == system]
        assert got and all(isinstance(r[5], Decimal) and r[5] == abs(raw[(r[1], r[2], r[3])][1]) *
                           (1 if r[5] > 0 else -1) for r in got)


def test_difference_3_debit_credit_columns_and_signed_amount_become_one_signed_amount(db):
    with (DATA / "erp_a_export_synthetic.csv").open(encoding="utf-8", newline="") as fh:
        a = list(csv.DictReader(fh, delimiter=";"))
    signed = {(r[2], r[3]): r[5] for r in entries(db) if r[1] == "ERP_A"}
    assert any(r["sollbetrag"] for r in a) and any(r["habenbetrag"] for r in a)
    for row in a:
        value = signed[(row["belegnummer"], int(row["zeile"]))]
        assert (value > 0) == bool(row["sollbetrag"]) and (value < 0) == bool(row["habenbetrag"])
    b_signs = {r[5] > 0 for r in entries(db) if r[1] == "ERP_B"}
    assert b_signs == {True, False}


def test_difference_4_column_names_are_the_same_for_both_sources(db):
    names = [r[0] for r in db.execute("DESCRIBE staging.ledger_entry").fetchall()]
    assert names == COLUMNS
    assert not {"belegnummer", "buchungsdatum", "doc_id", "posting_date"} & set(names)


def test_difference_5_charts_of_accounts_map_to_group_accounts_per_source_system(db):
    rows = entries(db)
    assert all(r[8] is not None for r in rows)  # every entry has a group account
    codes = {}
    for r in rows:
        codes.setdefault(r[7], {}).setdefault(r[1], r[8])
    both = {c: g for c, g in codes.items() if len(g) == 2}
    assert both and all(g["ERP_A"] != g["ERP_B"] for g in both.values())  # AC-04: 4710
    assert "4710" in both


# ---- known values and traceability -------------------------------------------------------------

def test_every_row_equals_the_generators_expected_entries(db):
    spec = importlib.util.spec_from_file_location("gen_e2e", DATA / "generate.py")
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    with tempfile.TemporaryDirectory() as tmp:
        expected = gen.generate(Path(tmp))
    assert entries(db) == [tuple(e[c] for c in COLUMNS) for e in expected]


def test_every_entry_traces_to_its_raw_record(db):
    raw = raw_records()
    got = entries(db)
    assert len(got) == len(raw)
    for r in got:
        assert raw[(r[1], r[2], r[3])] == (r[4], r[5], r[7])


def test_raw_erp_b_keeps_nesting_and_erp_a_keeps_text(db):
    assert db.execute("SELECT typeof(lines) FROM raw.erp_b_export LIMIT 1").fetchone()[0].endswith("[]")
    assert db.execute("SELECT typeof(sollbetrag) FROM raw.erp_a_export LIMIT 1").fetchone() == ("VARCHAR",)


# ---- run output ------------------------------------------------------------------------------

def test_run_succeeds_and_prints_in_contract_order(run_once):
    lines = run_once["lines"]
    assert run_once["code"] == 0
    positions = [
        next(i for i, line in enumerate(lines) if line.startswith(prefix))
        for prefix in ("source_system", "PASS\t01_completeness", "PASS\t02_mapping",
                       "exceptions_report.csv: ", "reserved: cost_center_model",
                       "2 gates run; both gates of unified_gl passed")
    ]
    assert positions == sorted(positions)
    assert [line for line in lines if line.startswith("reserved:")] == [
        "reserved: cost_center_model", "reserved: epm", "reserved: functional_model"]


def test_summary_has_one_row_per_system_and_currency_present_in_the_entries(run_once, db):
    lines = run_once["lines"]
    header = next(i for i, line in enumerate(lines) if line.startswith("source_system"))
    printed = []
    for line in lines[header + 1:]:
        if line.startswith(("PASS", "FAIL")):
            break
        printed.append(line.split())
    expected = db.execute(
        "SELECT source_system, transaction_currency, count(*), "
        "sum(signed_amount) FILTER (WHERE signed_amount > 0), "
        "-sum(signed_amount) FILTER (WHERE signed_amount < 0) FROM staging.ledger_entry "
        "GROUP BY 1, 2 ORDER BY 1, 2").fetchall()
    assert printed == [[s, c, str(n), str(d), str(k)] for s, c, n, d, k in expected]
    assert {p[1] for p in printed} >= {"EUR", "GBP", "USD"}


def test_exceptions_line_matches_the_file_and_content(run_once):
    path = ROOT / "build/unified_gl/exceptions_report.csv"
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["source_system", "source_document", "source_line", "original_description"]
    assert f"exceptions_report.csv: {len(rows) - 1} records" in run_once["lines"]
    assert len(rows) > 1
    assert {r[0] for r in rows[1:]} == {"ERP_A"}
    assert {r[3] for r in rows[1:]} == {
        "Bewirtung Kundentermin", "Wartungsvertrag Aufzug",
        "Sonderabschreibung Fuhrpark", "Rückstellung Rechtsstreit"}


def test_report_json_lists_both_gates(run_once):
    report = json.loads((ROOT / "build/report.json").read_text())
    assert [(r["gate"], r["status"], r["violations"]) for r in report] == [
        ("01_completeness", "PASS", 0), ("02_mapping", "PASS", 0)]


# ---- AC-12: nothing but build/ is written ----------------------------------------------------

def test_run_leaves_every_file_outside_build_unchanged(run_once):
    assert run_once["before"] == run_once["after"]
    for name in INPUTS:
        assert "synthetic" in name
        assert f"products/unified_gl/data/{name}" in run_once["after"]
