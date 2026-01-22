.PHONY: setup train test run docker-up fmt lint type loadtest

setup:
	python -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -r requirements.txt

train:
	. .venv/bin/activate && python -m src.training.train

test:
	. .venv/bin/activate && python -m pytest -q

run:
	. .venv/bin/activate && python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

docker-up:
	docker compose up --build

fmt:
	. .venv/bin/activate && python -m ruff format .

lint:
	. .venv/bin/activate && python -m ruff check .

type:
	. .venv/bin/activate && python -m mypy src

loadtest:
	. .venv/bin/activate && python scripts/load_test.py
