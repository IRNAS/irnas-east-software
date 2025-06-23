# Example project walk-through

This example showcases the use of `east` tool by using the NCS [example application] repository as a
starting point.

**Note:** The link above and `east init` below both reference the `v3.0.0` version of the example
application, to ensure that the example works. Other versions of the example application might not
work with the steps described in this document, since the example application changes over time.

## Setup

Initialize `my-workspace` folder for the `example-application`.

```bash
east init -m https://github.com/nrfconnect/ncs-example-application/ --mr v3.0.0 east-example
cd east-example/ncs-example-application
```

Run east update afterwards, to pull all the required repositories:

```bash
east update # This is equivalent to `west update`
```

### Toolchain installation

To install the required toolchain run:

```bash
east install toolchain
```

East determines the correct version of the toolchain from the `west.yml` manifest file and downloads
it to the host machine. The toolchain only needs to be installed once per every NCS version and not
per project. Some NCS versions share the same toolchain, which is also handled by `east`.

## Building, flashing and connecting

To build the application firmware:

```bash
cd app

# classic build
east build -b custom_plank

# using Twister test-suite configurations
east build -b custom_plank . -T app.default
east build -b custom_plank . -T app.debug
```

`custom_plank` is a slight modification of the `nrf52840dk`, so if you have one, you can use the
following command to flash the firmware to the device:

```bash
east flash
```

## RTT logs

The app logs to UART by default. To build the application with RTT support:

1. Create a `rtt.conf` file next to the `prj.conf` file with the following content:

   ```ini
   CONFIG_USE_SEGGER_RTT=y
   CONFIG_LOG_BACKEND_UART=y
   ```

In `sample.yaml`, add rtt.conf to the debug test-suite configuration:

```yaml
tests:
  app.default: {}
  app.debug:
    extra_overlay_confs:
      - debug.conf
      - rtt.conf
```

Rebuild:

```bash
east build -b custom_plank . -T app.debug
```

To view RTT logs:

```bash
# Run in first terminal window
east util connect

# Run in second, new, terminal window
east util rtt
```

## Creating a release

Creating a release is done in two steps:

1. Use [Twister] to build all applications we want to be part of the release.
2. Use `east pack` to extract relevant files and prepare a release package.

The `east pack` command is configured by using a `east.yml` file. For details, see
[configuration.md](configuration.md).

The steps below describe a minimal basic setup to get it working.

1. Create a `east.yml` file in the root folder with below content:

   ```yaml
   pack:
     artifacts:
       - $APP_DIR/zephyr/zephyr.hex
       - $APP_DIR/zephyr/zephyr.bin
       - merged.hex
   ```

2. Use [Twister] to build the `app` for both boards:

   ```bash
   # Run from the root of the repository
   east twister -T app \
     --build-only \
     --overflow-as-errors \
     -p custom_plank \
     -p nrf54l15dk/nrf54l15/cpuapp
   ```

3. Use `east pack` to extract the files from the build and prepare a release package:

   ```bash
   east pack --tag v0.1.0
   ```

   A folder named `package` will be created.

[example application]: https://github.com/nrfconnect/ncs-example-application/tree/v3.0.0
[Twister]: https://docs.zephyrproject.org/latest/develop/test/twister.html
