.PHONY: install dev test lint schemas manifests self-test api release

install:
	python -m pip install -e .

dev:
	python -m pip install -e '.[all]'

test:
	pytest

lint:
	ruff check src tests scripts
	pyright

schemas:
	python scripts/export_schemas.py

manifests:
	python scripts/build_docs_manifest.py
	python scripts/build_manifest.py

self-test:
	kompiler self-test

api:
	kompiler serve

release:
	python scripts/build_release.py
