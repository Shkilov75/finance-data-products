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
        files={"gates/01_g.sql": "CREATE TABLE staging.gate_ran AS SELECT 1 AS x;"
                                 " SELECT * FROM staging.t WHERE x = 0;"},
    )
    with pytest.raises(InvariantViolation):
        runner.run(cfg)
    import duckdb
    con = duckdb.connect(str(cfg.db_path), read_only=True)
    tables = {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    assert "second_ran" not in tables   # the later invariant did not run
    assert "gate_ran" not in tables     # and neither did the gate


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


# --- review 2026-11-07 F4: runner contract and manifest robustness ---------------------------

def _leave_earlier_run(cfg, name="demo"):
    build = cfg.root / "build"
    (build / name).mkdir(parents=True, exist_ok=True)
    (build / name / "exceptions_report.csv").write_text("old")
    (build / "report.json").write_text("[]")
    (build / "fdp.duckdb").write_text("old")
    (build / "keep.txt").write_text("keep")
    return build


def test_manifest_error_leaves_no_file_of_an_earlier_run(tmp_path):
    from fdp_core.errors import ManifestError
    cfg = make_product(tmp_path)
    build = _leave_earlier_run(cfg)
    (tmp_path / "products/demo/product.toml").write_text('name = "demo"\n')  # status missing
    with pytest.raises(ManifestError):
        runner.run(cfg)
    assert not (build / "report.json").exists()
    assert not (build / "demo").exists()
    assert not (build / "fdp.duckdb").exists()
    assert (build / "keep.txt").exists()


def test_unknown_status_is_a_manifest_error(tmp_path):
    from fdp_core.errors import ManifestError
    cfg = make_product(tmp_path, status="resrved")
    with pytest.raises(ManifestError, match="status"):
        runner.run(cfg)


@pytest.mark.parametrize("name", ["", "..", "a/b", "Demo", "demo x"])
def test_unsafe_product_name_is_a_manifest_error_and_deletes_nothing(tmp_path, name):
    from fdp_core.errors import ManifestError
    cfg = make_product(tmp_path)
    build = _leave_earlier_run(cfg)
    (tmp_path / "products/demo/product.toml").write_text(
        f'name = "{name}"\nstatus = "active"\nsql = ["sql/a.sql"]\n')
    with pytest.raises(ManifestError, match="name"):
        runner.run(cfg)
    assert (build / "keep.txt").exists()
    assert (tmp_path / "products/demo/product.toml").exists()


@pytest.mark.parametrize("target", ["../escape.csv", "/tmp/escape.csv", "sub/../../escape.csv"])
def test_export_file_outside_the_product_build_folder_is_a_manifest_error(tmp_path, target):
    from fdp_core.errors import ManifestError
    cfg = make_product(tmp_path, exports=[("reports/exceptions.sql", target)])
    with pytest.raises(ManifestError, match="export"):
        runner.run(cfg)
    assert not (tmp_path / "build/escape.csv").exists()


def test_export_without_query_or_file_is_a_manifest_error(tmp_path):
    from fdp_core.errors import ManifestError
    cfg = make_product(tmp_path, manifest_extra='[[exports]]\nfile = "x.csv"\n')
    with pytest.raises(ManifestError, match="query"):
        runner.run(cfg)


@pytest.mark.parametrize("kind, files, kwargs", [
    ("invariant", {"invariants/broken.sql": "SELECT * FROM nope"}, {"invariants": ["invariants/broken.sql"]}),
    ("gate", {"gates/broken.sql": "SELECT * FROM nope"}, {"gates": ["gates/broken.sql"]}),
    ("summary", {"reports/broken.sql": "SELECT * FROM nope"}, {"summary": "reports/broken.sql"}),
    ("export", {"reports/broken.sql": "SELECT * FROM nope"},
     {"exports": [("reports/broken.sql", "x.csv")]}),
])
def test_sql_failure_in_any_phase_names_the_file(tmp_path, kind, files, kwargs):
    from fdp_core.errors import LayerBuildError
    cfg = make_product(tmp_path, files=files, **kwargs)
    with pytest.raises(LayerBuildError, match=r"demo/.*broken\.sql"):
        runner.run(cfg)
    assert not cfg.report_path.exists()


# --- review 2026-11-07 round 2, G1: export file name and clean start -------------------------

@pytest.mark.parametrize("target", ["", ".", "..", "sub/x.csv", "a b.csv"])
def test_export_file_must_be_a_bare_file_name(tmp_path, target):
    from fdp_core.errors import ManifestError
    cfg = make_product(tmp_path, exports=[("reports/exceptions.sql", target)])
    with pytest.raises(ManifestError, match="export"):
        runner.run(cfg)
    assert not (tmp_path / "build/demo").is_file()


def test_manifest_export_error_is_raised_at_parse_time(tmp_path):
    from fdp_core.errors import ManifestError
    cfg = make_product(tmp_path, exports=[("reports/exceptions.sql", "")])
    with pytest.raises(ManifestError, match="export"):
        runner.discover_products(cfg)


def test_a_file_in_place_of_the_product_build_folder_is_replaced(tmp_path):
    cfg = make_product(tmp_path, exports=[("reports/exceptions.sql", "x.csv")])
    (tmp_path / "build").mkdir()
    (tmp_path / "build/demo").write_text("not a folder")
    runner.run(cfg)
    assert (tmp_path / "build/demo/x.csv").is_file()
    runner.run(cfg)  # and the next run works too
    assert (tmp_path / "build/demo/x.csv").is_file()


def test_a_symlink_in_place_of_the_product_build_folder_is_not_followed(tmp_path):
    cfg = make_product(tmp_path, exports=[("reports/exceptions.sql", "x.csv")])
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (outside / "old.csv").write_text("keep")
    (tmp_path / "build").mkdir()
    (tmp_path / "build/demo").symlink_to(outside, target_is_directory=True)
    runner.run(cfg)
    assert not (tmp_path / "build/demo").is_symlink()
    assert (tmp_path / "build/demo/x.csv").is_file()
    assert (outside / "old.csv").read_text() == "keep"   # the target of the link is left alone
    assert not (outside / "x.csv").exists()
