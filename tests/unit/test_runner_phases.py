import json

import pytest
from helpers import make_product

from fdp_core import runner
from fdp_core.errors import FdpError, InvariantViolation


def test_invariant_with_rows_raises_and_names_rows(tmp_path):
    cfg = make_product(tmp_path, invariants=["invariants/bad.sql"])
    with pytest.raises(InvariantViolation) as exc:
        runner.run(cfg)
    assert "DOC1" in str(exc.value)
    assert isinstance(exc.value, FdpError)
    assert not cfg.report_path.exists()


def test_invariant_failure_runs_before_gates_and_stops_later_invariants(tmp_path):
    cfg = make_product(
        tmp_path,
        invariants=["invariants/bad.sql", "invariants/bad2.sql"],
        gates=["gates/01_g.sql"],
    )
    with pytest.raises(InvariantViolation):
        runner.run(cfg)
    import duckdb
    con = duckdb.connect(str(cfg.db_path), read_only=True)
    tables = {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    assert "second_ran" not in tables


def test_zero_row_invariant_lets_gates_run(tmp_path):
    cfg = make_product(tmp_path, invariants=["invariants/ok.sql"])
    results = runner.run(cfg).gates
    assert [r.name for r in results] == ["01_g"]
    assert cfg.report_path.exists()


def test_manifest_without_new_keys_still_works(tmp_path):
    cfg = make_product(tmp_path)
    (tmp_path / "products/demo/product.toml").write_text(
        'name = "demo"\nstatus = "active"\nsql = ["sql/a.sql"]\ngates = ["gates/01_g.sql"]\n'
    )
    product = runner.discover_products(cfg)[0]
    assert product.invariants == [] and product.summary is None and product.exports == []
    assert [r.status for r in runner.run(cfg).gates] == ["PASS"]


def test_engine_placeholder_replaced(tmp_path):
    cfg = make_product(tmp_path, sql=["adapters/{engine}/load.sql", "sql/a.sql"])
    assert cfg.engine == "duckdb"
    runner.run(cfg)
    import duckdb
    con = duckdb.connect(str(cfg.db_path), read_only=True)
    assert con.execute("SELECT v FROM raw.loaded").fetchone() == (7,)


def test_layer_sql_failure_is_layer_build_error(tmp_path):
    from fdp_core.errors import LayerBuildError
    cfg = make_product(tmp_path, files={"sql/a.sql": "SELECT * FROM nope;"})
    with pytest.raises(LayerBuildError):
        runner.run(cfg)


def test_stale_report_and_product_build_folder_removed(tmp_path):
    cfg = make_product(tmp_path, invariants=["invariants/bad.sql"])
    cfg.report_path.parent.mkdir(parents=True)
    cfg.report_path.write_text(json.dumps([{"gate": "stale"}]))
    stale_dir = cfg.root / "build" / "demo"
    stale_dir.mkdir()
    (stale_dir / "old.csv").write_text("x")
    other = cfg.root / "build" / "keep.txt"
    other.write_text("keep")
    with pytest.raises(InvariantViolation):
        runner.run(cfg)
    assert not cfg.report_path.exists()
    assert not stale_dir.exists()
    assert other.exists()
