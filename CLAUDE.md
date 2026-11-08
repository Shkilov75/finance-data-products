# finance-data-products

Finance data products on DuckDB, with SQL quality gates. Architecture: `docs/architecture-map.md`, decisions: `docs/adr/`.

## Layout
- `src/fdp_core/` shared engine (runner, gates, config, errors, CLI `fdp`)
- `products/<name>/` one folder per product: `product.toml`, `sql/`, `gates/`, `data/`, `README.md`
- `databricks/` second execution path (planned, unverified)
- `tests/unit`, `tests/integration`

## Commands
- `make setup` create venv and install with dev extras
- `make run` build `build/fdp.duckdb` (layers raw, staging, mart) and run all gates
- `make demo-bad` runs `fdp run --bad`: it takes effect once a product has corrupted data to switch to, and the gates are then expected to FAIL. For `unified_gl` that is roadmap step 4; until then the flag does nothing and the run exits 0 like `make run`
- `make test` (`pytest`), `make lint` (`ruff check .`)

## Conventions
- Gate = one SQL file `products/<p>/gates/NN_<name>.sql`; zero returned rows means PASS. A failed gate is a result, not an exception; the runner exits non-zero on any FAIL.
- SQL stays dialect-neutral (runs on DuckDB and Spark SQL); dialect differences go into the `databricks/` adapter.
- The DuckDB file is rebuilt from scratch each run; there is no migration tool.
- IDs are deterministic hashes of business keys, never random UUIDs.
- Products never import each other; a dependent product reads the upstream `mart` tables.
- Shared behaviour lives in `src/fdp_core/`, never copied into a product.
