# Getting started

`east` intends to be fully documented inside the tool itself, (which is not
yet). Executing `east` or `east --help` on the command line should give you
sufficient information on how to use the tool in basic ways.

In the current state `east` does not fully replace `west` (and it is not yet
clear, if it ever will), so `west` tool still needs to be installed on the
system.

<!-- prettier-ignore -->
> [!NOTE]
> Preferred operating system to use is Linux, specifically Ubuntu 24.04
> or later. Older versions of Ubuntu or 20.04 and 22.04 are also supported.
> MacOS users can also use `east` and `west` tools, however at the moment of
> writing this instructions it is not clear what exact additional packages are
> needed to be installed. Windows is not supported at the moment.

## Installation

Use the Python package manager [pipx](https://github.com/pypa/pipx) to install
`east` and `west`:

```bash
pipx install east-tool west
```

If using Ubuntu versions earlier than 24.04, you need to install `east` and
`west` with pip:

```bash
pip install east-tool west
```

### Additional packages and tools

East depends on some additional tooling that users need to install manually.
Some of these packages are different between Ubuntu versions.

#### Common

```bash
sudo apt install build-essential curl
```

#### Libcurses

If on Ubuntu 20.04 or 22.04:

```bash
sudo apt install libcurses5
```

If on Ubuntu 24.04 or later:

```bash
sudo apt install libcurses6
```

#### Libffi

If on Ubuntu 20.04:

```bash
sudo apt install libffi7
```

If on Ubuntu 22.04 or later:

```bash
wget http://es.archive.ubuntu.com/ubuntu/pool/main/libf/libffi/libffi7_3.3-4_amd64.deb
sudo dpkg -i libffi7_3.3-4_amd64.deb
```

#### J-Link

J-Link Software and documentation pack is needed to flash the firmware to the
device:

1. Navigate to their [download page],
2. select latest version of the software and download the 64-bit DEB Installer.
3. Install it with below command:

   ```bash
   sudo dpkg -i <path-to-downloaded-deb-file>
   ```

[download page]: https://www.segger.com/downloads/jlink/

#### pylink-square

Install `pylink-square` dependency required by the Zephyr. If on Ubuntu 20.04 or
22.04:

```bash
pip install pylink-square
```

If on Ubuntu 24.04 or later:

```bash
pipx install pylink-square
```

For older versions of NCS (before `v3.0.0`) the now deprecated [nRF Command Line
Tools] (`nrfjprog`) is needed to flash the firmware to the device:

1. Scroll down to the Downloads section.
2. Choose Linux x86 64 as a platform.
3. Download `nrf-command-line-tools_10.24.2_amd64.deb` file
4. Install the downloaded package with below command:

   ```bash
   sudo dpkg -i <path-to-file>/nrf-command-line-tools_10.24.2_amd64.deb
   ```

[nRF Command Line Tools]:
  https://www.nordicsemi.com/Products/Development-tools/nRF-Command-Line-Tools

### First time system setup

`east` needs some tools installed on the host system to function.

This can be done with below command:

```
east install nrfutil-toolchain-manager
```

**Note**: You can install more tools with `east install --all` command, however
this is not needed for this getting started guide.

## Example project walk-through

Below example showcases the use of `east` tool by using Zephyr's [example
application] repository as a starting point.

[example application]:
  https://github.com/zephyrproject-rtos/example-application/tree/v3.1.0

**Note:** Above link and below `east init` both reference the `v3.1.0` version
of the example application. The `HEAD` of the `main` branch is currently broken
/ not compatible with this guide.

### Setup

Initialize `my-workspace` folder for the `example-application`.

```bash
east init -m https://github.com/zephyrproject-rtos/example-application --mr v3.1.0 my-workspace
cd my-workspace/example-application
```

#### Convert repository into a NCS project

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

#### Toolchain installation

To install required toolchain run below command:

```bash
east install toolchain
```

East determines the correct version of the toolchain from the `west.yml`
manifest file and downloads it to the host machine. Toolchain only needs to be
installed once per every NCS version and not per project.

#### Board overlay files

This examples uses `nrf52840dk_nrf52840` and `nrf52dk_nrf52832` boards, so we
need to create board overlay files for them:

```bash
cp app/boards/nucleo_f302r8.overlay app/boards/nrf52840dk_nrf52840.overlay
cp app/boards/nucleo_f302r8.overlay app/boards/nrf52dk_nrf52832.overlay
sed -i 's/gpioc/gpio0/g' app/boards/nrf52840dk_nrf52840.overlay
sed -i 's/gpioc/gpio0/g' app/boards/nrf52dk_nrf52832.overlay
```

Above two `sed` commands open both `.overlay` files that you just copied and
replace in both every occurrence of `gpioc` to `gpio0` (Nordic chips index their
ports with numbers instead with letters).

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
[Example project walk-through](#Example-project-walk-through) section before
continuing.

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
          - debug.conf
          - rtt.conf
```

Enter `app` folder and run below set of commands:

```bash
mkdir conf
mv prj.conf conf/common.conf
mv debug.conf conf
mv rtt.conf conf
```

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
