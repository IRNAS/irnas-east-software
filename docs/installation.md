# Installation

This document provides instructions for installing the necessary tools and dependencies to be able
to use `east`.

In the current state `east` does not fully replace `west` (and it is not yet clear, if it ever
will), so `west` tool still needs to be installed on the system.

<!-- prettier-ignore -->
> [!NOTE]
> Preferred operating system to use is Linux, specifically Ubuntu 24.04
> or later. Ubuntu 22.04 is also supported.
> MacOS users can also use `east` and `west` tools, however at the moment of
> writing this instructions it is not clear what exact additional packages are
> needed to be installed. Windows is not supported at the moment.

Use the Python package manager [pipx](https://github.com/pypa/pipx) to install `east` and `west`:

```bash
pipx install east-tool west
```

If using Ubuntu versions earlier than 24.04, you need to install `east` and `west` with pip:

```bash
pip install east-tool west
```

## Additional packages and tools

East depends on some additional tooling that users need to install manually. Some of these packages
are different between Ubuntu versions.

### Common

```bash
sudo apt install build-essential curl
```

### Libcurses

If on Ubuntu 22.04:

```bash
sudo apt install libncurses5
```

If on Ubuntu 24.04 or later:

```bash
sudo apt install libncurses6
```

### Libffi

```bash
wget http://es.archive.ubuntu.com/ubuntu/pool/main/libf/libffi/libffi7_3.3-4_amd64.deb
sudo dpkg -i libffi7_3.3-4_amd64.deb
```

### J-Link

J-Link Software and documentation pack is needed to flash the firmware to the device:

1. Navigate to their [download page],
2. select latest version of the software and download the 64-bit DEB Installer.
3. Install it with below command:

   ```bash
   sudo dpkg -i <path-to-downloaded-deb-file>
   ```

[download page]: https://www.segger.com/downloads/jlink/

### pylink-square

Install `pylink-square` dependency required by the Zephyr.

If on Ubuntu 22.04:

```bash
pip install pylink-square
```

If on Ubuntu 24.04 or later:

```bash
pipx install pylink-square
```

For older versions of NCS (before `v3.0.0`) the now deprecated [nRF Command Line Tools] (`nrfjprog`)
is needed to flash the firmware to the device:

1. Scroll down to the Downloads section.
2. Choose Linux x86 64 as a platform.
3. Download `nrf-command-line-tools_10.24.2_amd64.deb` file
4. Install the downloaded package with below command:

   ```bash
   sudo dpkg -i <path-to-file>/nrf-command-line-tools_10.24.2_amd64.deb
   ```

## First time system setup

`east` needs some tools installed on the host system to function.

This can be done with below command:

```bash
east install nrfutil-toolchain-manager
```

**Note**: You can install more tools with `east install --all` command, however they are not
required for the basic usage of `east`.
