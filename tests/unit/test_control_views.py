from decimal import Decimal

import duckdb
import pytest

from fdp_core.config import LAYERS, repo_root

ROOT = repo_root()
ADAPTER = ROOT / "products/unified_gl/adapters/duckdb"
STAGED = ROOT / "docs/features/unified-gl-inputs/migrations"
FILES = ("01_create_raw_inputs.sql", "02_create_typed_views.sql", "03_create_control_views.sql")


@pytest.fixture
def con(monkeypatch):
    monkeypatch.chdir(ROOT)
    connection = duckdb.connect()
    for layer in LAYERS:
        connection.execute(f"CREATE SCHEMA {layer}")
    for name in FILES:
        connection.execute((ADAPTER / name).read_text())
    yield connection
    connection.close()


def a_row(con, *, doc="BA-1", line="1", date="06.01.2026", account="4710", debit="10,00",
          credit="", currency="EUR"):
    con.execute("DELETE FROM raw.erp_a_export")
    con.execute("INSERT INTO raw.erp_a_export VALUES (?,?,?,?,?,?,?,'x')",
                [doc, line, date, account, debit, credit, currency])
    return con.execute("SELECT count(*), max(signed_amount) FROM raw.control_erp_a").fetchone()


def b_row(con, *, date="01/06/2026", amount="10.00", account="4710", currency="USD"):
    con.execute("DELETE FROM raw.erp_b_export")
    con.execute("INSERT INTO raw.erp_b_export VALUES ('B1',?,?,"
                "[{'line_no':'1','account':?,'amount':?,'memo':'Rent'}])",
                [date, currency, account, amount])
    return con.execute("SELECT count(*), max(signed_amount) FROM raw.control_erp_b").fetchone()


def test_clean_data_one_row_per_raw_entry_all_readable(con):
    for view, raw in (("control_erp_a", "erp_a_export"),
                      ("control_erp_b", "(SELECT unnest(lines) FROM raw.erp_b_export)")):
        source = raw if raw.startswith("(") else f"raw.{raw}"
        total = con.execute(f"SELECT count(*) FROM {source}").fetchone()[0]
        rows = con.execute(f"SELECT count(*), count(signed_amount) FROM raw.{view}").fetchone()
        assert rows == (total, total)


def test_readable_rows_have_signed_amounts(con):
    assert a_row(con, debit="1.234,56") == (1, Decimal("1234.56"))
    assert a_row(con, debit="", credit="1.234,56") == (1, Decimal("-1234.56"))
    assert b_row(con, amount="-1,234.56") == (1, Decimal("-1234.56"))
    assert b_row(con, amount="1,234.56") == (1, Decimal("1234.56"))


@pytest.mark.parametrize("kwargs", [
    {"date": "31.02.2026"},                        # not a real date
    {"debit": "5,00", "credit": "5,00"},           # both filled
    {"debit": "", "credit": ""},                   # both empty
    {"debit": "-5,00"},                            # negative
    {"debit": "0,00"},                             # zero amount
    {"debit": "", "credit": "0,00"},               # zero credit
    {"debit": "10,005"},                           # 3 decimals
    {"line": "x"},                                 # unreadable line
    {"doc": ""},                                   # empty document
    {"currency": ""},                              # empty currency
    {"account": ""},                               # empty account
])
def test_erp_a_unreadable_rule_keeps_row_with_null_amount(con, kwargs):
    assert a_row(con, **kwargs) == (1, None)


@pytest.mark.parametrize("kwargs", [
    {"date": "13/45/2026"},
    {"amount": "0.00"},
    {"amount": "0"},
    {"amount": "10.005"},
    {"amount": "abc"},
    {"account": ""},
    {"currency": ""},
])
def test_erp_b_unreadable_rule_keeps_row_with_null_amount(con, kwargs):
    assert b_row(con, **kwargs) == (1, None)


def test_control_agrees_with_typed_views_on_clean_data(con):
    a = con.execute("""
        SELECT count(*) FROM raw.control_erp_a c JOIN raw.typed_erp_a t
          ON c.document = t.document AND c.line = t.line
         AND c.entry_date = t.entry_date AND c.local_account = t.local_account
         AND c.currency = t.currency
         AND c.signed_amount = CASE WHEN t.debit_filled THEN t.debit ELSE -t.credit END
    """).fetchone()[0]
    b = con.execute("""
        SELECT count(*) FROM raw.control_erp_b c JOIN raw.typed_erp_b t
          ON c.document = t.document AND c.line = t.line
         AND c.entry_date = t.entry_date AND c.local_account = t.local_account
         AND c.currency = t.currency AND c.signed_amount = t.amount
    """).fetchone()[0]
    assert a == con.execute("SELECT count(*) FROM raw.control_erp_a").fetchone()[0] > 0
    assert b == con.execute("SELECT count(*) FROM raw.control_erp_b").fetchone()[0] > 0


def test_control_sql_never_touches_typed_views():
    code = "\n".join(line.split("--", 1)[0]
                     for line in (ADAPTER / "03_create_control_views.sql").read_text().splitlines())
    assert "typed_" not in code and "raw.erp_a_export" in code and "raw.erp_b_export" in code


def test_staged_pair_applies_and_reverts_cleanly(con):
    con.execute((STAGED / "03_create_control_views.down.sql").read_text())
    views = {r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'raw'").fetchall()}
    assert not {"control_erp_a", "control_erp_b"} & views
    con.execute((STAGED / "03_create_control_views.up.sql").read_text())


def test_live_file_is_the_promoted_staged_file():
    assert (ADAPTER / "03_create_control_views.sql").read_text() == (
        STAGED / "03_create_control_views.up.sql").read_text()
