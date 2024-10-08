install:
	@pip install --editable ".[dev]"

# With -s option the printf's are actually printed, otherwise they are
# sileneced.
test:
	pytest -s

format:
	ruff check . --fix
	ruff format .

build:
	@python3 -m build

upload-test:
	@twine upload -r testpypi dist/*

upload:
	@twine upload dist/*

version:
	@echo "Next version will be:"
	@python3 -m setuptools_scm
