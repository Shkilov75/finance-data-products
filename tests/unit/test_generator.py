import hashlib
import importlib.util
from decimal import Decimal

from fdp_core.config import repo_root

GENERATOR = repo_root() / "products/unified_gl/data/generate.py"
FILES = [
    "erp_a_export_synthetic.csv",
    "erp_b_export_synthetic.json",
    "account_mapping_synthetic.csv",
    "description_translation_synthetic.csv",
    "rates_synthetic.csv",
]


def load():
    spec = importlib.util.spec_from_file_location("unified_gl_generate", GENERATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(folder):
    return {n: hashlib.sha256((folder / n).read_bytes()).hexdigest() for n in FILES}


def test_two_runs_write_five_identical_files(tmp_path):
    gen = load()
    first, second = tmp_path / "one", tmp_path / "two"
    gen.generate(first)
    gen.generate(second)
    assert sorted(p.name for p in first.iterdir()) == sorted(FILES)
    assert digest(first) == digest(second)


def test_returns_expected_aligned_entries(tmp_path):
    entries = load().generate(tmp_path)
    assert 200 <= len(entries) <= 500
    sample = entries[0]
    assert {"entry_id", "source_system", "source_document", "source_line", "signed_amount",
            "transaction_currency", "local_account", "group_account", "description",
            "original_description", "entry_date"} <= set(sample)
    assert isinstance(sample["signed_amount"], Decimal)
    expected_id = hashlib.md5(
        f"{sample['source_system']}|{sample['source_document']}|{sample['source_line']}".encode()
    ).hexdigest()
    assert sample["entry_id"] == expected_id


def test_main_prints_counts_and_returns_zero(tmp_path, capsys):
    assert load().main(tmp_path) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("erp_a_export_synthetic.csv: ") and out[0].endswith(" entries")
    assert out[1].startswith("erp_b_export_synthetic.json: ") and out[1].endswith(" entries")


def test_main_returns_3_when_file_cannot_be_written(tmp_path, capsys):
    blocked = tmp_path / "file"
    blocked.write_text("not a folder")
    assert load().main(blocked) == 3
