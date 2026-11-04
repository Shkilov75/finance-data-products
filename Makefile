VENV := .venv
BIN := $(VENV)/bin

.PHONY: setup run demo-bad test lint clean

setup:
	python3 -m venv $(VENV)
	$(BIN)/pip install --quiet -e ".[dev]"

run:
	$(BIN)/fdp run

demo-bad:
	$(BIN)/fdp run --bad

test:
	$(BIN)/pytest

lint:
	$(BIN)/ruff check .

clean:
	rm -rf build $(VENV)
