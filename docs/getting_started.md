# Getting started

`east` intends to be fully documented inside the tool itself, (which is not
yet). Executing `east` or `east --help` on the command line should give you
sufficient information on how to use the tool in basic ways.

In the current state `east` does not fully replace `west` (and it is not yet
clear, if it ever will), so `west` tool still needs to be installed on the
system.

## Installation

Use the Python package manager [pip](https://pip.pypa.io/en/stable/) to install
and/or update `east`:

```bash
pip install --upgrade east-tool
```

To install `west` refer to its
[documentation](https://docs.zephyrproject.org/latest/develop/west/install.html).

## First time system setup

`east` needs some programs installed on the host system, to function.

This can be done with below command:

```
east sys-setup
```

## Example use walk-through

Below example showcases the use of `east` tool by using Zephyr's [example
application] repository as a starting point.

[example application]: https://github.com/zephyrproject-rtos/example-application

### Initialization

Initialize `my-workspace` folder for the `example-application`.

```bash
west init -m https://github.com/zephyrproject-rtos/example-application --mr main my-workspace
cd my-workspace/example-application
```

### Convert repository into a NCS project

Open `west.yml` and overwrite it with below snippet:

```yaml
manifest:
  remotes:
    - name: nrfconnect
      url-base: https://github.com/nrfconnect

  projects:
    - name: nrf
      repo-path: sdk-nrf
      remote: nrfconnect
      revision: v2.2.0
      import: true
```

Run west update afterwards:

```bash
west update
```

There is no need to overwrite the contents of the `west.yml`, if it already
imports NCS repo. Only `west update` is needed in that case.

### Toolchain installation

To install required toolchain run below command:

```bash
east update toolchain
```

East determines the correct version of the toolchain from the `west.yml`
manifest file and downloads it to the host machine. Toolchain only needs to be
installed once per every NCS version and not per project.

### Building, flashing and connecting

To build the application firmware:

```bash
cd app
east build -b nrf52840dk_nrf52840
```

To flash the firmware:

```bash
east flash
```

To view RTT logs:

```bash
# Run in first terminal window
east util connect

# Run in second, new, terminal window
east util rtt
```

## Creating a release

`east release` command, performs a release process consisting of a series of
`east build` commands to build applications and samples listed in the `east.yml`
file. Key component of release command are also _build types_.

Explanation on how `east.yml` and _build types_ work is explained in
[configuration.md](configuration.md) file.

Below steps describe minimal basic setup to get it working.

### Prerequisites

Make sure that you performed all steps described in
[Example use walk-through](#Example-use-walk-through) section before continuing.

Create a `east.yml` file in the root folder with below content:

```yaml
apps:
  - name: example_app
    west-boards:
      - nrf52840dk_nrf52840
      - nrf52dk_nrf52832

    build-types:
      - type: debug
        conf-files:
          - debug.conf
      - type: rtt
        conf-files:
          - rtt.conf
```

Enter `app` folder and run below set of commands:

```bash
mkdir conf
mv prj.conf conf/common.conf
mv debug.conf conf
mv rtt.conf conf
cp boards/nucleo_f302r8.overlay boards/nrf52840dk_nrf52840.overlay
cp boards/nucleo_f302r8.overlay boards/nrf52dk_nrf52832.overlay
```

Open both `.overlay` files that you just copied and replace in both every
occurrence of `gpioc` to `gpio0` (Nordic chips index their ports with numbers
instead with letters).

### Release

You can now run release command:

```
east release
```

Release procedure will build 6 different builds:

- For each west board:
  - Implicit **release** build using only `common.conf` (previously `prj.conf`)
  - **debug** build using `common.conf` and `debug.conf`
  - **rtt** build using `common.conf` and `rtt.conf`

Build artefacts can be found inside of `release` folder in the root directory.
