.DEFAULT_GOAL := help

SRC_DIR = fafsa_edit_rule_processor
TEST_DIR = tests

UV = uv
PYTHON = python3 # specify 3.14, if necessary
RUN = $(UV) run
PYTEST = $(RUN) $(PYTHON) -m pytest
TY = $(RUN) ty
RUFF = $(RUN) ruff

clean-venv:
	rm -rf .venv
.PHONY: clean-venv

clean: clean-venv
	find . -path ./venv -prune -o -name __pycache__ -print | xargs rm -rf
.PHONY: clean

sync:
	$(UV) sync
.PHONY: sync

lock:
	$(UV) lock
.PHONY: lock

ty:
	$(TY) check
.PHONY: ty

ruff:
	$(RUFF) check
.PHONY: ruff

lint: ty ruff
	$(RUN) ruff format --check
.PHONY: lint

format:
	$(RUFF) format
.PHONY: format

test:
	$(PYTEST) --cov $(SRC_DIR) --cov-report xml --cov-report term --cov-report html -vvv $(TEST_DIR)/unit
.PHONY: test

run:
	$(RUN) uvicorn fafsa_edit_rule_processor.main:create_app --factory --host 0.0.0.0 --port 8000 --reload
.PHONY: run

help:
	@echo 'usage: make <command>'
	@echo 'commands:'
	@echo '    clean                 clean created object files, remove virtual environment'
	@echo '    sync                  create uv environment from pyproject.toml'
	@echo '    lock                  use uv to generate dependency lock file'
	@echo '    ty                    type checking with ty'
	@echo '    ruff                  linting with ruff'
	@echo '    lint                  linting and type checking'
	@echo '    format                ruff to format'
	@echo '    test                  execute unit tests'
	@echo '    run                   run service'
.PHONY: help
