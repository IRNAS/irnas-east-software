# East configuration

The `east` tool provides a way to specify the project-specific configuration.
The configuration is done with an `east.yml` file, which needs to be placed in
the _root directory_ of the repo.

Currently, the configuration is required for:

- specifying available build types for applications and samples available
  through `--build-type` option which can be given to the `east build` command,
- specifying binary assets that will be created with the `east release` command.

This document describes the required fields of the `east.yml` file, how to use
_build-types_ and how to set up the project using the `east release` command.

## General structure of the configuration file

`east.yml` contains two main keys:

- `apps` - lists **one** or **more** applications with their own specific
  configurations.
- `samples` - lists **one** or **more** samples which can inherit configurations
  from applications.

Below is an example file with comments that can be copied into a project and
modified:

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
- Calling `east build` without the `--build-type` option will use `common.conf`
  automatically (`east` performs a search to determine which `common.conf`
  should be used).
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

## Release command

Command `east release` builds every single combination of firmware which is
listed in the `east.yml` file.

Different hardware versions of listed boards are picked up automatically from
the `board` directory.

Generally, this means:

```
* Create a binary for each `app`
    * for each hardware version of the `west-board`
        * for each `build-type`
```

and

```
* Create a binary for each `sample`
    * for each hardware version of the `west-board`
        * for `build-type` (either inherited or just `prj.conf`)
```

Created binaries are named according to the [IRNAS's release artefact naming
guidelines]. Samples are placed into a separate folder to avoid confusion.

`east release` accepts the software version which is injected into the binaries
(this depends on the modules used) and is added to the created file names.

## Resources for beginners

This document assumes knowledge of several different concepts:

- [Kconfig documentation page] - the main page about KConfig
- [One time CMake Arguments] - How to specify additional conf files to `Cmake`,
  `east` uses that under the hood
- [Nice blog about Zephyr configuration]

[irnas's release artefact naming guidelines]:
  https://github.com/IRNAS/irnas-guidelines-docs/blob/dev/docs/github_projects_guidelines.md#release-artefacts-naming-scheme-
[kconfig documentation page]:
  https://docs.zephyrproject.org/2.6.0/guides/kconfig/index.html
[one time cmake arguments]:
  https://docs.zephyrproject.org/3.1.0/develop/west/build-flash-debug.html#one-time-cmake-arguments
[nice blog about zephyr configuration]:
  https://www.jaredwolff.com/optimize-zephyr-config-and-overlays/
