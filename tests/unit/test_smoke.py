import duckdb

from fdp_core import runner
from fdp_core.cli import main
from fdp_core.config import Config, repo_root


def test_cli_runs_unified_gl_and_lists_reserved_products(capsys):
    assert main(["run"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert "2 gates run; both gates of unified_gl passed" in out
    assert [line for line in out if line.startswith("reserved:")] == [
        "reserved: cost_center_model", "reserved: epm", "reserved: functional_model"]
    assert "exceptions_report.csv: " in "\n".join(out)


def test_products_command_shows_one_active_and_three_reserved(capsys):
    assert main(["products"]) == 0
    assert sorted(capsys.readouterr().out.splitlines()) == [
        "cost_center_model\treserved", "epm\treserved", "functional_model\treserved",
        "unified_gl\tactive"]


def test_run_works_from_a_subdirectory(monkeypatch, capsys):
    monkeypatch.chdir(repo_root() / "docs")
    assert main(["run"]) == 0
    assert "2 gates run" in capsys.readouterr().out


def test_layers_built():
    cfg = Config(root=repo_root())
    runner.run(cfg)
    con = duckdb.connect(str(cfg.db_path), read_only=True)
    schemas = {r[0] for r in con.execute("SELECT schema_name FROM information_schema.schemata").fetchall()}
    assert {"raw", "staging", "mart"} <= schemas


def test_all_four_products_discovered():
    names = {p.name for p in runner.discover_products(Config(root=repo_root()))}
    assert names == {"unified_gl", "cost_center_model", "functional_model", "epm"}
