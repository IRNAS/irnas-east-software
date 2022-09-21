# East tool

## Installation and updating

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install East.

```bash
pip install --upgrade east-tool
```

## Usage

`east` intends to be fully documented inside the tool itself, so deduplication
of documentation is avoided. Executing `east` or `east --help` in the command
line should give you sufficient information on how to use the tool.

## Developing East

For development and testing of `east` the use of `virtualenv` is suggested.

Install `virtualenv`:
```bash
pip install virtualenv
```

Create and activate `virtualenv`, run this from project root:

```bash
virtualenv venv
source venv/bin/activate
```

To make development of the python package more smooth you can run below command
from the project root directory.
Changes that you make in the source code will be automatically available
instead of running `pip install .` all time.
```bash
pip install --editable .
```
