import importlib.util
import tempfile
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

from fdp_core.config import LAYERS, repo_root

ROOT = repo_root()
ADAPTER = ROOT / "products/unified_gl/adapters/duckdb"
STAGING = ROOT / "products/unified_gl/sql/staging/04_create_staging_ledger_entry.sql"
STAGED = ROOT / "docs/features/unified-gl-inputs/migrations"
COLUMNS = ["entry_id", "source_system", "source_document", "source_line", "entry_date",
           "signed_amount", "transaction_currency", "local_account", "group_account",
           "description", "original_description"]


@pytest.fixture
def con(monkeypatch):
    monkeypatch.chdir(ROOT)
    connection = duckdb.connect()
    for layer in LAYERS:
        connection.execute(f"CREATE SCHEMA {layer}")
    for name in ("01_create_raw_inputs.sql", "02_create_typed_views.sql"):
        connection.execute((ADAPTER / name).read_text())
    yield connection
    connection.close()


def build(con):
    con.execute(STAGING.read_text())


def rows(con, where="true"):
    return con.execute(f"SELECT {', '.join(COLUMNS)} FROM staging.ledger_entry WHERE {where} "
                       "ORDER BY source_system, source_document, source_line").fetchall()


@pytest.fixture(scope="module")
def expected():
    spec = importlib.util.spec_from_file_location(
        "unified_gl_generate_t7", ROOT / "products/unified_gl/data/generate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as tmp:
        return module.generate(Path(tmp))


def test_every_entry_equals_the_generators_expected_entry(con, expected):
    build(con)
    got = rows(con)
    want = [tuple(e[c] for c in COLUMNS) for e in expected]
    assert len(got) == len(want) > 0
    assert got == want


def test_row_count_equals_readable_raw_entries(con):
    build(con)
    raw = (con.execute("SELECT count(*) FROM raw.typed_erp_a").fetchone()[0]
           + con.execute("SELECT count(*) FROM raw.typed_erp_b").fetchone()[0])
    assert con.execute("SELECT count(*) FROM staging.ledger_entry").fetchone() == (raw,)


def test_sign_convention_and_common_names_for_both_sources(con):
    build(con)
    for system in ("ERP_A", "ERP_B"):
        pos, neg, zero = con.execute(
            "SELECT count(*) FILTER (WHERE signed_amount > 0), "
            "count(*) FILTER (WHERE signed_amount < 0), "
            "count(*) FILTER (WHERE signed_amount = 0) "
            "FROM staging.ledger_entry WHERE source_system = ?", [system]).fetchone()
        assert pos > 0 and neg > 0 and zero == 0
    assert [r[0] for r in con.execute("DESCRIBE staging.ledger_entry").fetchall()] == COLUMNS


def test_same_account_code_maps_differently_per_source_system(con):
    build(con)
    groups = dict(con.execute(
        "SELECT source_system, any_value(group_account) FROM staging.ledger_entry "
        "WHERE local_account = '4710' GROUP BY source_system").fetchall())
    assert set(groups) == {"ERP_A", "ERP_B"} and groups["ERP_A"] != groups["ERP_B"]


def test_entry_without_mapping_stays_with_null_group_account(con):
    con.execute("DELETE FROM raw.account_mapping WHERE source_system = 'ERP_B' "
                "AND local_account = '4710'")
    build(con)
    got = rows(con, "source_system = 'ERP_B' AND local_account = '4710'")
    assert got and all(r[8] is None for r in got)
    assert all(r[8] is not None for r in rows(con, "source_system = 'ERP_A'"))


def test_untranslated_description_keeps_original_and_entry_stays(con):
    build(con)
    untranslated = rows(con, "description = original_description AND source_system = 'ERP_A'")
    assert {r[9] for r in untranslated} == {
        "Bewirtung Kundentermin", "Wartungsvertrag Aufzug",
        "Sonderabschreibung Fuhrpark", "Rückstellung Rechtsstreit"}


@pytest.mark.parametrize("variant", ["MIETE BÜROGEBÄUDE", "Miete", "Miete Bürogebäude "])
def test_translation_needs_exact_whole_text(con, variant):
    con.execute("DELETE FROM raw.erp_a_export")
    con.execute("INSERT INTO raw.erp_a_export VALUES "
                "('BA-1','1','06.01.2026','4710','10,00','','EUR',?)", [variant])
    build(con)
    assert rows(con)[0][9] == variant          # not translated: whole text must be equal
    assert rows(con)[0][10] == variant         # original_description is kept as the source wrote it
    listed = con.execute((ROOT / "products/unified_gl/reports/exceptions_report.sql").read_text()).fetchall()
    assert [r[3] for r in listed] == [variant]


def test_exact_text_is_translated(con):
    con.execute("DELETE FROM raw.erp_a_export")
    con.execute("INSERT INTO raw.erp_a_export VALUES "
                "('BA-1','1','06.01.2026','4710','10,00','','EUR','Miete Bürogebäude')")
    build(con)
    assert rows(con)[0][9] == "Office building rent"


@pytest.mark.parametrize("a_values", [
    ("BA-1", "1", "31.02.2026", "4710", "10,00", "", "EUR"),   # bad date
    ("BA-1", "1", "06.01.2026", "4710", "10,00", "5,00", "EUR"),  # both filled
    ("BA-1", "1", "06.01.2026", "4710", "", "", "EUR"),         # both empty
    ("BA-1", "1", "06.01.2026", "4710", "-10,00", "", "EUR"),   # negative
    ("BA-1", "1", "06.01.2026", "4710", "0,00", "", "EUR"),     # zero
    ("BA-1", "1", "06.01.2026", "4710", "10,005", "", "EUR"),   # 3 decimals
    ("BA-1", "1", "06.01.2026", "4710", "", "12.5", "EUR"),      # credit: misplaced thousands dot
    ("BA-1", "1", "06.01.2026", "4710", "", "10,005", "EUR"),    # credit: 3 decimals
    ("BA-1", "1", "06.01.2026", "4710", "", "1.23,45", "EUR"),   # credit: broken grouping
    ("BA-1", "1", "06.01.2026", "4710", "", "-5,00", "EUR"),     # credit: negative
    ("BA-1", "1", "06.01.2026", "4710", "", "0,00", "EUR"),      # credit: zero
    ("BA-1", "1", "06.01.2026", "4710", "10,00", "", ""),       # empty currency (AC-09)
    ("BA-1", "1", "06.01.2026", "", "10,00", "", "EUR"),        # empty account
])
def test_unreadable_entry_is_absent(con, a_values):
    con.execute("DELETE FROM raw.erp_a_export")
    con.execute("INSERT INTO raw.erp_a_export VALUES (?,?,?,?,?,?,?,'x')", list(a_values))
    build(con)
    assert rows(con, "source_system = 'ERP_A'") == []


def test_line_01_and_1_give_same_entry_id(con):
    con.execute("DELETE FROM raw.erp_a_export")
    con.execute("INSERT INTO raw.erp_a_export VALUES "
                "('BA-1','01','06.01.2026','4710','10,00','','EUR','x')")
    build(con)
    first = rows(con)[0][0]
    con.execute("DROP TABLE staging.ledger_entry")
    con.execute("UPDATE raw.erp_a_export SET zeile = '1'")
    build(con)
    assert rows(con)[0][0] == first
    assert rows(con)[0][3] == 1


def test_entry_id_is_32_hex_and_stable_between_builds(con):
    build(con)
    first = rows(con)
    con.execute("DROP TABLE staging.ledger_entry")
    build(con)
    assert rows(con) == first
    assert all(len(r[0]) == 32 and int(r[0], 16) >= 0 for r in first)


def test_signed_amount_scale_two(con):
    build(con)
    typ = con.execute("SELECT typeof(signed_amount) FROM staging.ledger_entry LIMIT 1").fetchone()
    assert typ == ("DECIMAL(18,2)",)
    assert isinstance(rows(con)[0][5], Decimal)


def test_live_file_has_no_file_reading_and_equals_staged_design():
    code = "\n".join(line.split("--", 1)[0] for line in STAGING.read_text().splitlines()).lower()
    for forbidden in ("read_csv", "read_json", "read_parquet", "strptime", "regexp", "try_cast"):
        assert forbidden not in code
    assert STAGING.read_text() == (STAGED / "04_create_staging_ledger_entry.up.sql").read_text()


def test_staged_down_reverts_cleanly(con):
    build(con)
    con.execute((STAGED / "04_create_staging_ledger_entry.down.sql").read_text())
    assert con.execute("SELECT count(*) FROM information_schema.tables "
                       "WHERE table_schema = 'staging'").fetchone() == (0,)


def test_two_entries_of_one_document_with_equal_date_account_and_amount_keep_distinct_ids(con):
    """AC-06 precondition: only the line tells these two apart (also in ERP B)."""
    con.execute("DELETE FROM raw.erp_a_export")
    con.execute("INSERT INTO raw.erp_a_export VALUES "
                "('BA-1','1','06.01.2026','4710','10,00','','EUR','x'),"
                "('BA-1','2','06.01.2026','4710','10,00','','EUR','x')")
    con.execute("DELETE FROM raw.erp_b_export")
    con.execute("INSERT INTO raw.erp_b_export VALUES ('B1','01/06/2026','USD',["
                "{'line_no':'1','account':'4710','amount':'10.00','memo':'x'},"
                "{'line_no':'2','account':'4710','amount':'10.00','memo':'x'}])")
    build(con)
    entries = rows(con)
    assert len(entries) == 4
    for system in ("ERP_A", "ERP_B"):
        pair = [r for r in entries if r[1] == system]
        assert len(pair) == 2
        assert pair[0][4:9] == pair[1][4:9]          # same date, amount, currency, account, group
        assert pair[0][0] != pair[1][0]              # but different identifiers
    assert len({r[0] for r in entries}) == 4


# --- review 2026-11-07 round 2, G3 (and G2 c): a blank translation target is untranslated ----

@pytest.mark.parametrize("target", ["", " ", "   "])
def test_blank_translation_target_keeps_the_original_description_and_is_reported(con, target):
    con.execute("DELETE FROM raw.erp_a_export")
    con.execute("INSERT INTO raw.erp_a_export VALUES "
                "('BA-1','1','06.01.2026','4710','10,00','','EUR','Miete Bürogebäude')")
    con.execute("UPDATE raw.description_translation SET common_description = ? "
                "WHERE original_description = 'Miete Bürogebäude'", [target])
    build(con)
    entry = rows(con)[0]
    assert entry[9] == "Miete Bürogebäude"      # not blank: the original text stays
    assert entry[10] == "Miete Bürogebäude"
    listed = con.execute((ROOT / "products/unified_gl/reports/exceptions_report.sql").read_text()).fetchall()
    assert [r[3] for r in listed] == ["Miete Bürogebäude"]


@pytest.mark.parametrize("memo", ["Rent ", " Rent", "RENT"])
def test_erp_b_translation_needs_exact_whole_text_too(con, memo):
    con.execute("DELETE FROM raw.erp_a_export")
    con.execute("DELETE FROM raw.erp_b_export")
    con.execute("INSERT INTO raw.erp_b_export VALUES ('B1','01/06/2026','USD',"
                "[{'line_no':'1','account':'4710','amount':'10.00','memo':?}])", [memo])
    con.execute("DELETE FROM raw.description_translation WHERE source_system = 'ERP_B'")
    con.execute("INSERT INTO raw.description_translation VALUES ('ERP_B','Rent','Rent')")
    build(con)
    entry = rows(con)[0]
    assert entry[1] == "ERP_B"
    assert (entry[9], entry[10]) == (memo, memo)    # not translated, kept as the source wrote it
    listed = con.execute((ROOT / "products/unified_gl/reports/exceptions_report.sql").read_text()).fetchall()
    assert [r[3] for r in listed] == [memo]


# --- review 2026-11-07 round 3, H1: ERP B guards, per-source translation, padded document ----

@pytest.mark.parametrize("currency, account", [("", "4710"), (" ", "4710"), ("USD", ""), ("USD", " ")])
def test_erp_b_entry_with_empty_currency_or_account_is_absent(con, currency, account):
    con.execute("DELETE FROM raw.erp_a_export")
    con.execute("DELETE FROM raw.erp_b_export")
    con.execute("INSERT INTO raw.erp_b_export VALUES ('B1','01/06/2026',?,"
                "[{'line_no':'1','account':?,'amount':'10.00','memo':'x'}])", [currency, account])
    build(con)
    assert rows(con) == []


def test_translation_of_one_source_system_is_not_used_for_the_other(con):
    con.execute("DELETE FROM raw.erp_a_export")
    con.execute("DELETE FROM raw.erp_b_export")
    con.execute("INSERT INTO raw.erp_b_export VALUES ('B1','01/06/2026','USD',"
                "[{'line_no':'1','account':'4710','amount':'10.00','memo':'Miete Bürogebäude'}])")
    # the list translates this text for ERP_A only
    assert con.execute("SELECT count(*) FROM raw.description_translation WHERE source_system = 'ERP_A' "
                       "AND original_description = 'Miete Bürogebäude'").fetchone() == (1,)
    con.execute("DELETE FROM raw.description_translation WHERE source_system = 'ERP_B'")
    build(con)
    entry = rows(con)[0]
    assert entry[1] == "ERP_B" and (entry[9], entry[10]) == ("Miete Bürogebäude", "Miete Bürogebäude")
    listed = con.execute((ROOT / "products/unified_gl/reports/exceptions_report.sql").read_text()).fetchall()
    assert [r[3] for r in listed] == ["Miete Bürogebäude"]


def test_padded_document_number_gives_the_same_entry_id_as_the_trimmed_one(con):
    con.execute("DELETE FROM raw.erp_a_export")
    con.execute("INSERT INTO raw.erp_a_export VALUES "
                "('BA-1','1','06.01.2026','4710','10,00','','EUR','x')")
    build(con)
    first = rows(con)[0]
    con.execute("DROP TABLE staging.ledger_entry")
    con.execute("UPDATE raw.erp_a_export SET belegnummer = '  BA-1 '")
    build(con)
    assert rows(con)[0] == first and first[2] == "BA-1"
