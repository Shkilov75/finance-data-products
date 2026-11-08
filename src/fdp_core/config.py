from dataclasses import dataclass
from pathlib import Path

LAYERS = ("raw", "staging", "mart")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    root: Path
    bad: bool = False
    engine: str = "duckdb"

    @property
    def products_dir(self) -> Path:
        return self.root / "products"

    @property
    def db_path(self) -> Path:
        return self.root / "build" / "fdp.duckdb"

    @property
    def report_path(self) -> Path:
        return self.root / "build" / "report.json"

    def product_build_dir(self, product: str) -> Path:
        return self.root / "build" / product
