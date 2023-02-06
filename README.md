# East

`east` is a command line meta-tool, useful for creating, managing, and deploying
Zephyr or nRF Connect SDK (NCS) projects. It is built on top of Zephyr's RTOS
meta-tool, [West] and Nordic's [nRF Connect Toolchain Manager].

[west]: https://github.com/zephyrproject-rtos/west
[nrf connect toolchain manager]:
  https://github.com/NordicSemiconductor/pc-nrfconnect-toolchain-manager

`east` combines the above two tools and thus provides:

- Automated detection and installation of tooling required for NCS projects.
- Common `west` commands used for the development, such as `build`, `flash`,
  etc.
- Sandboxed development environment, thanks to the nRF Connect Toolchain
  Manager, every `build`, `flash`, etc. command runs inside of its toolchain
  environment.
- Automated process of generating release artefacts for your entire project, no
  matter the number of applications, samples or boards.
- Support for build types into the usual build process.
- RTT utility commands to connect and see the RTT stream.

## Reasoning behind `east`

There are several reasons why someone would like to create yet another tool on
top of `west`.

- Working on several projects at once means using different versions of the NCS
  repository and different versions of the toolchain. Managing these differences
  is not a trivial task.
- There is no reproducible build guarantee between the developer's machines.
  Slight differences between tool versions can manifest into hard-to-find bugs.
- Creating GitHub releases manually takes ages as you have to run the build
  process for every combination of the board, application, build variant, etc
  and properly rename the release binary. The release procedure gets longer with
  every addition of new hardware and build variation option.

`east` automates the above tasks and tries to make the developer more
productive.

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
