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
	flake8
	mypy --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs .

lint-strict:
	flake8 .
	mypy --strict .

.PHONY: install run debug clean lint lint-strict