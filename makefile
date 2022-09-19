install:
	@pip install --editable ".[dev]"

build:
	@python -m build

upload-test:
	@twine upload -r testpypi dist/*

upload:
	@twine upload dist/*

version:
	@echo "Next version will be:"
	@python -m setuptools_scm
