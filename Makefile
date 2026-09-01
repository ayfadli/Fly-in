install:
	uv pip install -r requirements.txt

run:
	uv run python3 -m src $(ARGS)

debug:
	uv run python3 -m pdb -m src $(ARGS)

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +

lint:
	uv run flake8 .
	uv run mypy src/ --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy src/ --strict