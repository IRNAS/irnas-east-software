install:
	@pip install --editable .

install-dev:
	@pip install --editable ".[dev]"

build:
	@python3 -m build

upload-test:
	@twine upload -r testpypi dist/*

upload:
	@twine upload dist/*

version:
	@echo "Next version will be:"
	@python3 -m setuptools_scm
