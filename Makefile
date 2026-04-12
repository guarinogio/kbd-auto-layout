PYTHON ?= python3
VENV ?= $(HOME)/.venvs/kbd-auto-layout
ACTIVATE = . $(VENV)/bin/activate
PREFIX ?= $(HOME)/.local
REPO_DIR := $(shell pwd)

.PHONY: venv install-dev format lint test run-cli run-daemon clean install-user uninstall-user

venv:
	$(PYTHON) -m venv $(VENV)
	$(ACTIVATE) && pip install --upgrade pip

install-dev: venv
	$(ACTIVATE) && pip install -e ".[dev]"

format:
	$(VENV)/bin/ruff format src tests

lint:
	$(VENV)/bin/ruff check src tests

test:
	$(VENV)/bin/pytest

run-cli:
	PYTHONPATH=$(REPO_DIR)/src $(PYTHON) -m kbd_auto_layout --help

run-daemon:
	PYTHONPATH=$(REPO_DIR)/src $(PYTHON) -m kbd_auto_layout.daemon

install-user:
	mkdir -p $(PREFIX)/bin
	printf '%s\n' '#!/usr/bin/env bash' \
	  'export PYTHONPATH="$(REPO_DIR)/src"' \
	  'exec python3 -m kbd_auto_layout.cli "$$@"' \
	  > $(PREFIX)/bin/kbd-auto-layoutctl
	printf '%s\n' '#!/usr/bin/env bash' \
	  'export PYTHONPATH="$(REPO_DIR)/src"' \
	  'exec python3 -m kbd_auto_layout.daemon "$$@"' \
	  > $(PREFIX)/bin/kbd-auto-layoutd
	sed -i 's|$(REPO_DIR)|$(REPO_DIR)|g' $(PREFIX)/bin/kbd-auto-layoutctl
	sed -i 's|$(REPO_DIR)|$(REPO_DIR)|g' $(PREFIX)/bin/kbd-auto-layoutd
	chmod +x $(PREFIX)/bin/kbd-auto-layoutctl $(PREFIX)/bin/kbd-auto-layoutd
	mkdir -p $(HOME)/.config/systemd/user
	cp packaging/systemd/kbd-auto-layout.service $(HOME)/.config/systemd/user/kbd-auto-layout.service
	mkdir -p $(PREFIX)/share/zsh/site-functions
	cp packaging/completions/zsh/_kbd-auto-layoutctl $(PREFIX)/share/zsh/site-functions/_kbd-auto-layoutctl
	systemctl --user daemon-reload || true
	@echo "Installed to $(PREFIX)/bin"
	@echo "Zsh completion installed to $(PREFIX)/share/zsh/site-functions"
	@echo "Enable with: systemctl --user enable --now kbd-auto-layout.service"

uninstall-user:
	rm -f $(PREFIX)/bin/kbd-auto-layoutctl
	rm -f $(PREFIX)/bin/kbd-auto-layoutd
	rm -f $(HOME)/.config/systemd/user/kbd-auto-layout.service
	rm -f $(PREFIX)/share/zsh/site-functions/_kbd-auto-layoutctl
	systemctl --user daemon-reload || true
	@echo "Uninstalled user-local binaries, completion, and service"

clean:
	rm -rf $(VENV) build dist *.egg-info .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
