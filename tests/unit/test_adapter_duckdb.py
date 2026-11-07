import csv
import json
from datetime import date
from decimal import Decimal

import duckdb
import pytest

from fdp_core.config import LAYERS, repo_root

ROOT = repo_root()
ADAPTER = ROOT / "products/unified_gl/adapters/duckdb"
DATA = ROOT / "products/unified_gl/data"
STAGED = ROOT / "docs/features/unified-gl-inputs/migrations"


@pytest.fixture
def con(monkeypatch):
    monkeypatch.chdir(ROOT)  # adapter paths are relative to the repository root
    connection = duckdb.connect()
    for layer in LAYERS:
        connection.execute(f"CREATE SCHEMA {layer}")
    for name in ("01_create_raw_inputs.sql", "02_create_typed_views.sql"):
        connection.execute((ADAPTER / name).read_text())
    yield connection
    connection.close()


def test_raw_tables_hold_the_rows_of_the_files(con):
    with (DATA / "erp_a_export_synthetic.csv").open(encoding="utf-8", newline="") as fh:
        a_rows = len(list(csv.DictReader(fh, delimiter=";")))
    docs = json.loads((DATA / "erp_b_export_synthetic.json").read_text(encoding="utf-8"))
    assert con.execute("SELECT count(*) FROM raw.erp_a_export").fetchone() == (a_rows,)
    assert con.execute("SELECT count(*) FROM raw.erp_b_export").fetchone() == (len(docs),)
    assert con.execute("SELECT sum(len(lines)) FROM raw.erp_b_export").fetchone() == (
        sum(len(d["lines"]) for d in docs),)
    for table in ("account_mapping", "description_translation", "exchange_rate"):
        assert con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0] > 0


def test_erp_b_lines_stay_nested_and_text(con):
    typ = con.execute("SELECT typeof(lines) FROM raw.erp_b_export LIMIT 1").fetchone()[0]
    assert typ.startswith("STRUCT(") and typ.endswith("[]")
    cols = {r[0]: r[1] for r in con.execute("DESCRIBE raw.erp_a_export").fetchall()}
    assert set(cols.values()) == {"VARCHAR"}


def test_typed_views_have_the_same_names_for_both_sources(con):
    a = {r[0] for r in con.execute("DESCRIBE raw.typed_erp_a").fetchall()}
    b = {r[0] for r in con.execute("DESCRIBE raw.typed_erp_b").fetchall()}
    common = {"source_system", "document", "line", "entry_date", "currency", "local_account",
              "description"}
    assert common <= a and common <= b
    assert {"debit", "credit", "debit_filled", "credit_filled"} <= a and "amount" in b


def test_five_source_differences_read_as_same_types(con):
    """Date format, number format, amount representation, column names, nesting."""
    con.execute("DELETE FROM raw.erp_a_export")
    con.execute("INSERT INTO raw.erp_a_export VALUES "
                "('BA-1','01','06.01.2026','4710','1.234,56','','EUR','Miete Bürogebäude'),"
                "('BA-1','02','06.01.2026','1200','','1.234,56','EUR','Miete Bürogebäude')")
    a = con.execute("SELECT entry_date, debit, credit, line, document FROM raw.typed_erp_a "
                    "ORDER BY line").fetchall()
    assert a == [(date(2026, 1, 6), Decimal("1234.56"), None, 1, "BA-1"),
                 (date(2026, 1, 6), None, Decimal("1234.56"), 2, "BA-1")]
    con.execute("DELETE FROM raw.erp_b_export")
    con.execute("INSERT INTO raw.erp_b_export VALUES ('B1','01/06/2026','USD',"
                "[{'line_no':'1','account':'4710','amount':'1,234.56','memo':'Rent'},"
                "{'line_no':'2','account':'1010','amount':'-1,234.56','memo':'Rent'}])")
    b = con.execute("SELECT entry_date, amount, line, document FROM raw.typed_erp_b "
                    "ORDER BY line").fetchall()
    assert b == [(date(2026, 1, 6), Decimal("1234.56"), 1, "B1"),
                 (date(2026, 1, 6), Decimal("-1234.56"), 2, "B1")]


@pytest.mark.parametrize("date_text", ["31.02.2026", "2026-01-06", "06/01/2026", "6.1.2026", ""])
def test_unreadable_erp_a_date_is_null(con, date_text):
    con.execute("DELETE FROM raw.erp_a_export")
    con.execute("INSERT INTO raw.erp_a_export VALUES ('BA-1','1',?,'4710','10,00','','EUR','x')",
                [date_text])
    assert con.execute("SELECT entry_date FROM raw.typed_erp_a").fetchone() == (None,)


@pytest.mark.parametrize("amount", ["1,234.56", "10,005", "abc", "-5,00", "1.23,45"])
def test_unreadable_erp_a_amount_is_null_but_cell_counts_as_filled(con, amount):
    con.execute("DELETE FROM raw.erp_a_export")
    con.execute("INSERT INTO raw.erp_a_export VALUES ('BA-1','1','06.01.2026','4710',?,'','EUR','x')",
                [amount])
    assert con.execute("SELECT debit, debit_filled FROM raw.typed_erp_a").fetchone() == (None, True)


def test_zero_is_filled_and_both_filled_keeps_both_flags(con):
    con.execute("DELETE FROM raw.erp_a_export")
    con.execute("INSERT INTO raw.erp_a_export VALUES "
                "('BA-1','1','06.01.2026','4710','0,00','','EUR','x'),"
                "('BA-1','2','06.01.2026','4710','5,00','5,00','EUR','x')")
    rows = con.execute("SELECT line, debit, debit_filled, credit_filled FROM raw.typed_erp_a "
                       "ORDER BY line").fetchall()
    assert rows == [(1, Decimal("0.00"), True, False), (2, Decimal("5.00"), True, True)]


@pytest.mark.parametrize("amount", ["1.234,56", "12.345", "1,234.567", "x", "--5.00"])
def test_unreadable_erp_b_amount_is_null(con, amount):
    con.execute("DELETE FROM raw.erp_b_export")
    con.execute("INSERT INTO raw.erp_b_export VALUES ('B1','01/06/2026','USD',"
                "[{'line_no':'1','account':'4710','amount':?,'memo':'Rent'}])", [amount])
    assert con.execute("SELECT amount FROM raw.typed_erp_b").fetchone() == (None,)


def test_unreadable_erp_b_date_is_null(con):
    con.execute("DELETE FROM raw.erp_b_export")
    con.execute("INSERT INTO raw.erp_b_export VALUES ('B1','13/45/2026','USD',"
                "[{'line_no':'1','account':'4710','amount':'5.00','memo':'Rent'}])")
    assert con.execute("SELECT entry_date FROM raw.typed_erp_b").fetchone() == (None,)


def test_committed_data_reads_completely(con):
    """No readable value is lost on the clean committed files."""
    assert con.execute("SELECT count(*) FROM raw.typed_erp_a WHERE entry_date IS NULL OR "
                       "(debit IS NULL AND credit IS NULL)").fetchone() == (0,)
    assert con.execute("SELECT count(*) FROM raw.typed_erp_b WHERE entry_date IS NULL OR "
                       "amount IS NULL").fetchone() == (0,)


def test_staged_down_scripts_revert_cleanly(con):
    for name in ("02_create_typed_views.down.sql", "01_create_raw_inputs.down.sql"):
        con.execute((STAGED / name).read_text())
    left = con.execute("SELECT table_name FROM information_schema.tables "
                       "WHERE table_schema = 'raw'").fetchall()
    assert left == []


def test_adapter_files_are_copies_of_the_staged_design():
    for adapter_name, staged_name in (("01_create_raw_inputs.sql", "01_create_raw_inputs.up.sql"),
                                      ("02_create_typed_views.sql", "02_create_typed_views.up.sql")):
        assert (ADAPTER / adapter_name).read_text() == (STAGED / staged_name).read_text()
