# East tool

## Installation and updating

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install East.

```bash
pip install --upgrade east-tool
```

## Usage

`east` intends to be fully documented inside the tool itself, (which is not
yet). Executing `east` or `east --help` in the command line should give you
sufficient information on how to use the tool in basic ways.

To learn more about configuration refer to the [docs](docs) folder.


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

To create and editable install of `east` run below command. Whatever change you
make in the code it will be immediately reflected in the actual tool.

```bash
make install-dev
```

### Running unit tests

```bash
make test
```

#### Editable install does not work

If `make install` (more exactly `pip install -e .`) ever misbehaves, it is
probably due to this: https://github.com/pypa/pip/issues/7953.

Run below command once and then again `make install`, this fixed it last time:

```bash
python3 -m pip install --prefix=$(python3 -m site --user-base) -e .
```

#### Test for version check fails

This happens if the `make install-dev` command was not run before running `make test`.
