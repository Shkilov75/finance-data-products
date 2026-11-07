import pytest
from helpers import make_product, make_reserved

from fdp_core import cli, report, runner
from fdp_core.gates import FAIL, PASS, GateResult

SUMMARY = "reports/summary.sql"
EXPORT = ("reports/exceptions.sql", "exceptions_report.csv")


@pytest.fixture
def run_cli(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "repo_root", lambda: tmp_path)

    def go(*argv):
        code = cli.main(list(argv))
        out = capsys.readouterr()
        return code, out.out, out.err

    return go


def test_render_table_aligns_numbers_right():
    text = report.render_table(["a", "n"], [("x", 5), ("yy", 1234)])
    lines = text.splitlines()
    assert lines[0].split() == ["a", "n"]
    assert lines[1].endswith("   5") and lines[2].endswith("1234")


def test_write_csv_header_only_lf(tmp_path):
    path = tmp_path / "out" / "e.csv"
    report.write_csv(path, ["a", "b"], [])
    assert path.read_bytes() == b"a,b\n"
    report.write_csv(path, ["a", "b"], [("x", 1)])
    assert path.read_bytes() == b"a,b\nx,1\n"


def test_format_gate_lines():
    lines = report.format_gate_lines([GateResult("g1", PASS), GateResult("g2", FAIL, [(1,), (2,)])])
    assert lines == ["PASS\tg1\t0 violating rows", "FAIL\tg2\t2 violating rows"]


def test_exit0_output_order_and_files(tmp_path, run_cli):
    make_product(tmp_path, summary=SUMMARY, exports=[EXPORT])
    make_reserved(tmp_path, "res_a")
    make_reserved(tmp_path, "res_b")
    code, out, _ = run_cli("run")
    assert code == 0
    lines = out.splitlines()
    idx = {k: next(i for i, line in enumerate(lines) if line.startswith(k))
           for k in ("source_system", "PASS\t01_g", "exceptions_report.csv: 0 records",
                     "reserved: res_a", "reserved: res_b", "1 gates run")}
    assert list(idx.values()) == sorted(idx.values())
    assert any("ERP_A" in line and "48210.40" in line for line in lines)
    assert lines[-1] == "1 gates run; the gate of demo passed"
    csv = (tmp_path / "build/demo/exceptions_report.csv").read_text()
    assert csv == "source_system,source_document,source_line,original_description\n"
    assert (tmp_path / "build/report.json").exists()


def test_two_gates_sentence(tmp_path, run_cli):
    make_product(tmp_path, gates=["gates/01_g.sql", "gates/02_g.sql"],
                 files={"gates/02_g.sql": "SELECT 1 WHERE 1 = 0"})
    code, out, _ = run_cli("run")
    assert code == 0
    assert out.splitlines()[-1] == "2 gates run; both gates of demo passed"


def test_exit1_prints_violating_rows_in_full_and_still_writes_files(tmp_path, run_cli):
    make_product(
        tmp_path, summary=SUMMARY, exports=[EXPORT],
        files={"gates/01_g.sql": "SELECT 'ERP_A EUR entries: raw 61, aligned 60' AS m "
                                 "UNION ALL SELECT 'ERP_A DOC-0007 line 2: missing' "},
    )
    make_reserved(tmp_path, "res_a")
    code, out, _ = run_cli("run")
    assert code == 1
    assert "FAIL\t01_g\t2 violating rows" in out
    assert "  ERP_A EUR entries: raw 61, aligned 60" in out
    assert "  ERP_A DOC-0007 line 2: missing" in out
    assert "exceptions_report.csv: 0 records" in out and "reserved: res_a" in out
    assert (tmp_path / "build/report.json").exists()
    assert (tmp_path / "build/demo/exceptions_report.csv").exists()
    assert "passed" not in out.splitlines()[-1]


def test_multi_column_violating_row_is_joined(tmp_path, run_cli):
    make_product(tmp_path, files={"gates/01_g.sql": "SELECT 'ERP_B' AS s, '4710' AS acc"})
    code, out, _ = run_cli("run")
    assert code == 1 and "  ERP_B 4710" in out


def test_exit2_invariant_violation(tmp_path, run_cli):
    make_product(tmp_path, summary=SUMMARY, exports=[EXPORT], invariants=["invariants/bad.sql"])
    stale = tmp_path / "build/demo"
    stale.mkdir(parents=True)
    (stale / "exceptions_report.csv").write_text("old")
    (tmp_path / "build/report.json").write_text("[]")
    code, out, err = run_cli("run")
    assert code == 2
    assert err.splitlines()[0] == "invariant violation: bad"
    assert "DOC1" in err
    assert "source_system" not in out and "PASS" not in out
    assert not (tmp_path / "build/report.json").exists()
    assert not (tmp_path / "build/demo/exceptions_report.csv").exists()


def test_exit3_layer_failure(tmp_path, run_cli):
    make_product(tmp_path, summary=SUMMARY, exports=[EXPORT], files={"sql/a.sql": "SELECT * FROM nope"})
    code, _out, err = run_cli("run")
    assert code == 3
    assert err.startswith("error: ") and "demo/sql/a.sql" in err
    assert not (tmp_path / "build/report.json").exists()
    assert not (tmp_path / "build/demo/exceptions_report.csv").exists()


def test_exit3_unexpected_exception_never_code_1(tmp_path, run_cli, monkeypatch):
    def boom(cfg):
        raise RuntimeError("boom")

    monkeypatch.setattr(runner, "run", boom)
    code, _, err = run_cli("run")
    assert code == 3 and err.strip() == "error: boom"


def test_exit3_malformed_manifest_on_products(tmp_path, run_cli):
    bad = tmp_path / "products/x"
    bad.mkdir(parents=True)
    (bad / "product.toml").write_text('name = "x"\n')
    code, _, err = run_cli("products")
    assert code == 3 and err.startswith("error: ")


def test_only_reserved_products(tmp_path, run_cli):
    make_reserved(tmp_path, "res_a")
    code, out, _ = run_cli("run")
    assert code == 0
    assert "0 gates run" in out and "reserved: res_a" in out
    assert "source_system" not in out and "records" not in out
