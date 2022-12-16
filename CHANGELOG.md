# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [Unreleased]

### Fixed

-   _east util rtt_ command, local echo option was not passed correctly.

## [0.6.1] - 2022-12-16

### Fixed

-   Case where there is not apps key in east.yml and we are building and app
    without build type was not correctly handled.

## [0.6.0] - 2022-12-15

### Added

-   _east release_ command. Usage is explained in the "doc/configuration.md".

## [0.5.0] - 2022-12-13

### Added

-   Command _east build_ will now after every build step copy
    `compile_commands.json`, if found, from the build directory to the project
    directory. This makes job of locating this file easier for clangd. Help
    description for _east build_ was updated to reflect that.

### Changed

-   Make east.yml optional for everything, except for the usage of east build
    command with --build-type option.
-   Make apps key and samples key inside east.yml optional. This is useful for
    driver projects, which do not need apps, or any project that might not have
    samples.

### Fixed

-   Properly handle _east build_ commands outside of applications and samples.
    This means that running _east build_ command will default to plain west
    behaviour, as it should.

## [0.4.0] - 2022-11-21

### Added

-   Support for --build-type option for build command. The use of this option is
    documented in detail in "docs/configuration.md". --build-type option was
    tested exhaustively with unit tests and various test fixtures with pytest. The
    tests can be found in tests folder.
-   Projects using east tool from now on need east.yml file in the root directory.
    See above mentioned document.

### Fixed

-   Error code propagation through Nordic's Toolchain Manager.

## [0.3.0] - 2022-10-05

### Added

-   _bypass_ command, which can take any set of arguments that west command
    supports and pass them directly to west tool.
-   _util connect_ and _util rtt_ commands. With first you connect to the device,
    with second you can observe RTT logs while connected.
-   _build_ and _flash_ commands now support extra positional arguments after
    double dash `--`. Run them with --help string to learn what do they do.

### Fixed

-   Incorrect no toolchain message.
-   \--force flag was not set as flag by Click.
-   \--jlink-id should be of type str but it was not.
-   No westdir related bug that came up in demonstration.

## [0.2.0] - 2022-10-03

### Added

-   _sys-setup_ command which will install system-wide dependencies to the host
    machine.
-   Global _--echo_ flag which echoes every shell command before executing it.
-   _update toolchain_ command - Command will download and install appropriate
    version of toolchain based on the detected NCS version. If NCS version is
    currently not supported it throws an error.

### Changed

-   Structure of the commands. Commands are now split into two groups: workspace
    commands and system commands. This is reflected in the project directory
    structure and help texts.
-   Workspace commands will now use downloaded toolchain whenever they can.

## [0.1.42] - 2022-09-20

### Added

-   Build command which can build firmware in current directory.
-   Flash command which flashes code binary.
-   Clean command which deletes build folder.
-   Styling look with rich click module.
-   Use newer pyproject.toml format for metadata specification.
-   MIT license file.
-   Makefile for development.
-   Docker scripts for building and running docker containers, for development
    purposes.

[Unreleased]: https://github.com/IRNAS/irnas-east-software/compare/v0.6.1...HEAD

[0.6.1]: https://github.com/IRNAS/irnas-east-software/compare/v0.6.0...v0.6.1

[0.6.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.5.0...v0.6.0

[0.5.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.4.0...v0.5.0

[0.4.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.3.0...v0.4.0

[0.3.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.2.0...v0.3.0

[0.2.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.1.42...v0.2.0

[0.1.42]: https://github.com/IRNAS/irnas-east-software/compare/5a4f734ca077a91cc2c77b42080f0c9814a489ed...v0.1.42
