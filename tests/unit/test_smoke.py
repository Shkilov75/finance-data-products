import duckdb

from fdp_core import runner
from fdp_core.cli import main
from fdp_core.config import Config, repo_root


def test_cli_boots_and_runs_empty_product_set(capsys):
    assert main(["run"]) == 0
    assert "0 gates run" in capsys.readouterr().out


def test_layers_built():
    cfg = Config(root=repo_root())
    runner.run(cfg)
    con = duckdb.connect(str(cfg.db_path), read_only=True)
    schemas = {r[0] for r in con.execute("SELECT schema_name FROM information_schema.schemata").fetchall()}
    assert {"raw", "staging", "mart"} <= schemas


def test_all_four_products_discovered():
    names = {p.name for p in runner.discover_products(Config(root=repo_root()))}
    assert names == {"unified_gl", "cost_center_model", "functional_model", "epm"}
