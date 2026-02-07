.PHONY: setup test run-web

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

test:
	python -m pytest

run-web:
	uvicorn src.web_app:app --reload
