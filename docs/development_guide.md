# Developing East

## Table of Contents

<!-- vim-markdown-toc GFM -->

- [Setup](#setup)
- [Running unit tests](#running-unit-tests)
- [Formatting](#formatting)
- [Known issues](#known-issues)
  - [Editable install does not work](#editable-install-does-not-work)
  - [Test for version check fails](#test-for-version-check-fails)

<!-- vim-markdown-toc -->

## Setup

To develop and test `east` the use of `virtualenv` virtual environment is highly
recommended.

Additionally, `makefile` file in the root directory contains most common
commands for interacting with the project.

1. Install `virtualenv`:

```bash
pip install virtualenv
```

2. Create and activate `virtualenv`, run this from the project root directory:

```bash
virtualenv venv
source venv/bin/activate
```

3. To create an editable install of `east` tool run the below command. Whatever
   change you make in the code will be immediately reflected if you run `east`
   on the command line afterwards.

```bash
make install
```

## Running unit tests

To run unit tests:

```bash
make test
```

## Formatting

To format the project run:

```bash
make format
```

## Known issues

### Editable install does not work

If `make install` or `make install-dev` (more exactly `pip install -e .`) ever
misbehaves, it is probably due to this: https://github.com/pypa/pip/issues/7953.

Run the below command once and then again `make install`, this fixed it last
time:

```bash
python3 -m pip install --prefix=$(python3 -m site --user-base) -e .
```

### Test for version check fails

This happens if the `make install-dev` command was not run before running
`make test`.
