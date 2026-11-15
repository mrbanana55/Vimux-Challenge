.PHONY: play status test

play:
	./play.sh

status:
	./play.sh --status

test:
	PYTHONPATH=src .venv/bin/pytest -v
