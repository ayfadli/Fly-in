install:
	uv pip install -r requirements.txt

run:
	python3 src/main.py $(ARGS)

debug:
	python3 -m pdb src/main.py $(ARGS)

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +

lint:
	uv run flake8 src/ --exclude=.venv
	uv run mypy src/ --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 src/ --exclude=.env
	uv run mypy src/ --strict