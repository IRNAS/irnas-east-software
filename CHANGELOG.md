# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [Unreleased]

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

[Unreleased]: https://github.com/IRNAS/irnas-east-software/compare/v0.2.0...HEAD

[0.2.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.1.42...v0.2.0

[0.1.42]: https://github.com/IRNAS/irnas-east-software/compare/5a4f734ca077a91cc2c77b42080f0c9814a489ed...v0.1.42
