# East configuration

The `east` tool provides a way to specify the project-specific configuration.
The configuration is done with an `east.yml` file, which needs to be placed in
the _root directory_ of the repository.

Currently, the configuration is required for:

- specifying available build types for applications and samples available
  through `--build-type` option which can be given to the `east build` command,
- specifying binary assets that will be created with the `east release` command.

`east.yml file` is optional; Users do not need to create to use `east`, however
it that case the above two mentioned functionalities will not work.

This document describes the expected contents of the `east.yml` file, what are
_build-types_, how to use them and how to specify binary assets for the
`east release` command.

## General structure of the configuration file

`east.yml` contains two main keys:

- `apps` - lists **one** or **more** applications with their own specific
  configurations. This key is optional (useful for driver projects).
- `samples` - lists **one** or **more** samples which can inherit configurations
  from applications. This key is optional (for projects that might not need
  samples).

Below is an example of `east.yml` with comments that can be copied into a
project and modified:

```yaml
apps:
  - name: nrf52_app
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf
      - type: uart
        conf-files:
          - debug.conf
          - uart.conf

  - name: nrf91_app
    west-boards:
      - nrf9160dk_nrf9160_ns

    build-types:
      - type: debug
        conf-files:
          - debug.conf

samples:
  - name: settings
    west-boards:
      - custom_nrf52840dk
    inherit-build-type:
      app: nrf52_app
      build-type: debug

  - name: dfu
    west-boards:
      - custom_nrf52840dk
    # Don't inherit, use prj.conf in the sample's folder.
```

## Build type

`east` introduces the concept of a _build type_ for building several images that
only differ from each other in KConfig options.

Build types are sets of Kconfig fragment files (`.conf` files) that are given to
CMake during the build system generation process.

Splitting your Kconfig fragments into distinct files means that:

- there is a clear separation of concerns, as each fragmented file deals with
  one specific idea,
- reusing configuration files between different projects is easier,
- the same sets of settings do not have to repeat in different files, thus
  lowering the chance of copy-paste mistakes.

The user specifies the exact set of Kconfig fragments for each build type in
`east.yml` under the `build-types` key:

```yaml
apps:
  - name: test_app
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf
      - type: uart
        conf-files:
          - debug.conf
          - uart.conf
```

A `build-types` key must have one or more objects which need to have the
following two keys:

- `type` - the name of the build type, used on the command line.
- `conf-files` - a list of the Kconfig fragments files that belong to this build
  type

When building an application image the user can specify the specific build type
with `--build-type` or `-u` flag, for example:

```bash
east build -b nrf52840dk_nrf52840 --build-type debug
```

There are a few rules that are related to the build types and the way they are
specified in `east.yml`:

- Each application needs to contain a `conf` folder which stores all conf files
  for that application. `east` will look for listed `conf-files` inside this
  folder.
- Each `conf` folder is required to contain a `common.conf` file which contains
  configuration _common_ to all build types. `common.conf` replaces the role of
  `prj.conf`, which is now **not allowed** to be used in applications (in
  samples it is still allowed).
- `common.conf` is always used with each build type, so it does not need to be
  explicitly specified in `conf-files`.
- Calling `east build` without the `--build-type` option will use **only**
  `common.conf`.
- Order of additional conf files matters, as they are applied in the order
  listed.
- As normal, conf files that are specific to the used `west` boards,
  (`nrf52840dk_nrf52840.conf`) for example, are picked up automatically and
  applied directly after `common.conf`, before other `.conf` files, however,
  they also need to be placed within the `conf` folder.

For example, taking the above rules and the example `east.yml` into account this
means that:

- When we do not specify the build type, only the `common.conf` is used.
- When we use the `debug` build type, `common.conf` and `debug.conf` are used.
- When we use the `uart` build type, `common.conf`, `debug.conf` and `uart.conf`
  are used.

### Release build type

Calling `east build` without the `--build-type` option just uses `common.conf`.
This kind of build type is known as a `release` build type.

Several things to note about the `release` build type:

- Samples can inherit configuration from a `release` build type, just like from
  the other build types (See _Samples_ section below).
- `release` build type does not appear as a misc qualifier, as do other build
  types, in the build artefact names when running `east release` command (see
  _Release command_ section below).
- Released firmware that has a `release` build type is considered as one and
  only firmware that should be used in the production.

## Applications

The application is the main program in an `east` workspace. The most common the
use-case is a GitHub repo with one application, however, repos with multiple
applications are also supported.

Depending on the number of applications the structure of the project needs to be
adjusted:

- If there is only one application, then its folders and files
  (`CmakeLists.txt`, `conf`, `src`, etc.) can be directly placed into the `app`
  folder.
- If there are multiple applications, then their folders and files need to be
  placed under separate folders inside the `app` folder, for example, below is a
  structure for the `multi_app` project that has two applications `nrf52` and
  `nrf91`:

```
example_project
├── app
│   ├── nrf52   # Here are CmakeLists.txt, conf, src, etc.
│   ├── nrf91   # Here are CmakeLists.txt, conf, src, etc.
├── boards
├── CMakeLists.txt
├── common
├── drivers
├── Kconfig
├── samples
├── west.yml
└── zephyr
```

To configure an application in `east.yml`, the user must specify which
`west-boards` and `build-types` are available.

## Samples

These are small programs that are located in the `samples` folder. Their purpose
is to test or demonstrate some specific module or library.

They do not require `conf` folders (as they are expected to test only one
thing), however, we can add KConfig fragment files to them in two ways:

- We use the `inherit-build-type` key in `east.yaml` to specify one which
  `build-type` from which `app` we would like to use.
- We do not use the `inherit-build-type` key in `east.yaml`, in that case,
  `east` uses default `west` behaviour.

In both cases we do not need to specify the `--build-type` option, `east` will
figure out what to do. Samples do not need to be specified in the `east.yml`
file for the `east build` command to work (but you can only use `prj.conf` in
that case).

An example sample section is below, imagine that it is below the above snippet
which is in _Build types section_:

```yaml
samples:
  - name: settings
    west-boards:
      - custom_nrf52840dk
    inherit-build-type:
      app: nrf52_app
      build-type: debug

  - name: dfu
    west-boards:
      - custom_nrf52840dk
    # Don't inherit, use default west behaviour in the `dfu` sample folder
```

### Nested samples

`samples` folder can contain nested sub-folders with samples.

For example, if we have a `blinky` sample located like this:

```text
example_project
├── samples
│   ├── basic
│   │   ├── blinky   # Blinky sample
```

then you would specify such sample in `east.yml` like this:

```yaml
samples:
  - name: basic/blinky
    west-boards:
      - custom_nrf52840dk
    inherit-build-type:
      app: nrf52_app
      build-type: debug
```

## Release command

`east release` command runs a release process consisting of a series of
`east build` commands to build applications and samples listed in the
`east.yml`. Created build artefacts are then renamed and placed into `release`
folder in project's root directory.

Version number is inferred from `git describe --tags --always --long --dirty=+`
command. If the `east release` command is run directly on a commit with a
version tag (such as `v1.0.2`), and there are no local changes, then only
version tag is added to the name of artefacts, otherwise the additional git hash
qualifier is added. If there is no tag then default of `v0.0.0` is used.

As both `apps` and `samples` keys in `east.yml` are optional, release process
for a specific key will be skipped, if it is not present.

Different hardware versions of listed boards are picked up automatically from
the `board` directory.

Created binaries are named according to the [IRNAS's release artefact
naming guidelines]. Samples are placed into a separate folder to avoid
confusion. A collection of zip files is created to simplify upload to GitHub
Release page.

High-level release process looks like this:

```
# Release process for applications:
# for each application:
#   for each west_board:
#     for each of its hardware revisions:
#       for every build type:
#         Run west build command with correct conf files
#         Create release subfolder with application binaries
#
# for each application:
#   for every build type:
#     Create a zip folder

# Release process for samples:
# for each samples:
#   for each west_board:
#     for each of its hardware revisions:
#         Run west build command with correct conf files
#         Create release subfolder with samples binaries
#
# Create a zip folder of samples
```

### Copied build artefacts

Which build artefacts are copied and renamed from `build/zephyr` to the
`release` subfolders depends on what kind of build was done:

- If a default build was done then `zephyr.bin`, `zephyr.hex`, `zephyr.elf`
  files are copied and renamed.
- If a MCUBoot or TF-M build was done then `dfu_application.zip`,
  `app_update.bin`, `merged.hex`, `zephyr.elf` files are copied and renamed.

In both cases the file extensions are preserved.

## Resources for beginners

This document assumes knowledge of several different concepts:

- [Kconfig documentation page] - the main page about KConfig
- [One time CMake Arguments] - How to specify additional conf files to `Cmake`, `east`
  uses that under the hood
- [Nice blog about Zephyr configuration]

[irnas's release artefact naming guidelines]:
  https://github.com/IRNAS/irnas-guidelines-docs/blob/dev/docs/github_projects_guidelines.md#release-artefacts-naming-scheme-
[kconfig documentation page]:
  https://docs.zephyrproject.org/2.6.0/guides/kconfig/index.html
[one time cmake arguments]:
  https://docs.zephyrproject.org/3.1.0/develop/west/build-flash-debug.html#one-time-cmake-arguments
[nice blog about zephyr configuration]:
  https://www.jaredwolff.com/optimize-zephyr-config-and-overlays/
