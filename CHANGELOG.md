# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [Unreleased]

## [0.16.3] - 2023-10-30

### Fixed

-   Error build message in `east release` command. It was also prettified.
-   Build type issue when building app not listed in the east.yaml, again. 
    See (#85) for the start of the issue and 7243ee4 for solution and rationale.

## [0.16.1] - 2023-09-29

### Changed

-   Transition to the trunk-based development model.

### Fixed

-   Incorrect conversion of output of a git command into endpoint in 
    `east store` command.

## [0.16.0] - 2023-09-28

### Added

-   Version check. East will now occasionally check for the latest version and notify
    the user when it is available.
-   Add `EAST_CODECHECKER_CI_MODE` environment variable. If running CodeChecker inside 
    continuous integration environment, run `export EAST_CODECHECKER_CI_MODE=1` before
    running any `east codechecker` commands. This will make `east` use the `CodeChecker` 
    executable that is on the system path instead of the one in the tooling directory. 
    System provided `CodeChecker` will normally also want to use the system provided 
    clang, clang-tidy and cppcheck programs. way users can leverage the programs  
    provided by continuous integration environment and not by `east`, which is usually 
    faster due to caching.
-   Add `--build-dir` option to the `east codechecker` commands. From now on, you do not 
    need to run `east codechecker` command from the same directory where `build` folder 
    is located. The default is still `build`, however you can specify a different one 
    with `--build-dir` option.
-   `east codechecker` commands now also take build directory location into account when
    generating a skip file.

### Changed

-   How previous build type of previously run build is detected. Previously `east`
    looked into the `image_preload.cmake` file and parsed its content to figure out the
    used build type. This approach worked well until someone wanted to append extra
    `.conf` files to the `CONFIG_OVERLAY`. To support this use case east now just
    creates a single file in the `build` dir and writes build type to it.

## [0.15.2] - 2023-09-28

### Fixed

-   Incorrect message that was shown when toolchain was not installed.
-   Fix east release for driver projects, which do not have `app` folder.

## [0.15.1] - 2023-09-27

### Removed

-   Python version check. This was mostly needed due to Conda binary, which is 
    not used any more.

### Fixed

-   Platform detection for clang tooling.

## [0.15.0] - 2023-09-26

### Breaking interface changes

-   This version of East created breaking changes in the interface. This was 
    done due to the consistency with existing `west` interface.
    Changes:
    -   `east sys-setup` was removed and replaced with `east install`.
    -   `east install` now contains several subcommands, which can be used to 
        install `codechecker`, `toolchain`, `nrfutil-toolchain-manager`, etc.
    -   `east update` is now just a wrapper around `west update` command.
    -   Newly added `east init` is now just a wrapper around `west init` command.

### Added

-   Support for Codechecker, a static analysis infrastructure. Newly added 
    command `east codechecker` contains several subcommands: 
    -   Users can now `check` their Zephyr projects with `clang-tidy` and 
        `clangsa`,
    -   apply suggested fixes with `fixit`,
    -   `store` the results of the Codechecker analysis to a server,
    -   `servdiff` - compare the local analysis against the last server analysis,
    -   See example `codechecker_config.yaml` file with `example-config`,
    -   or directly run any Codechecker command with `bypass`.
        An effort was made to make the `east codechecker check` command most useful:
    -   Most of the warnings that are reported because of the Zephyr's macros are 
        filtered out. 
    -   Installation of Codechecker and all its dependencies is seamless, you only 
        need to run `east install codechecker`.
-   Support for generating the Software Bill of Materials (SBOM) in SPDX format.
    To generate SPDX files add `--spdx` or `--spdx-app-only` flags to 
    `east build` or `east release` respectively. `east build` command will place 
    SPDX files in the build folder, while `east release` will generate them for 
    each combination of parameters and place them next to the respective 
    artefacts.
-   Add `EAST_BUILD_TYPE` CMake define to the build and release commands.
    This define is emitted only if we are building an app with build type 
    functionality (so, it is not emitted for samples). It contains a string, 
    identical to the given `--build-type` flag.

### Fixed

-   Build type issue when building app not listed in the east.yaml (#85)
-   `pykwalify` error caused by an empty east.yml (#85)
-   Always delete build folder when build settings do not match. (#85)
-   Incorrect removal of toolchain when using `--force` flag. (#85)
-   Improve error message when running bypass in non NCS repo. (#85)
-   Correctly handle ctrl+c when running `east debug`. Previously everything 
    broke (yes, everything), when user wanted to stop a running program inside 
    `gdb`. Essentially the ctrl+c combination was passed twice to `gdb`, which 
    caused all sort of problems.

### Removed

-   Conda from list of installed tools. Conda was originally intended to be used 
    as bootstrapping environment, however there was never need for it.

## [0.14.0] - 2023-08-24

### Added

-   Add `--shell` flag to the `east bypass` command. It launches a sub-shell within the
    current terminal inside the isolated environment provided by the Nordic's nRF
    Toolchain Manager.
-   `east twister` command. This command is just a wrapper for the `west twister`
    command which runs Twister, a test runner tool.
-   `east attach` command. This command is just a wrapper for the `west attach`
    command, which is similiar to the `west debug`.

### Changed

-   `east bypass` now passes arbitrary commands into directly into the Nordic's nRF
    Toolchain Manager instead into just West that is in the Manager. That way user can
    user use other executables and python programs provided by the toolchains in the
    Manager.
-   `east build`, `east flash` and `east debug` are now just wrappers for their 
    west counterparts. Due to this the internals and externals of the East could 
    be simplified. User experience did not change, the commands behave just like 
    they did before, they just do not directly provide help for possible 
    options and arguments, but instead instruct users to use `--extra-help` 
    option to learn more about west command counterparts. Due to this change the
    `attach` command was moved from `debug` command to its own place.

## [0.13.0] - 2023-07-26

### Removed

-   Conda install from `east sys-setup` command as it is not needed by East.

## [0.12.3] - 2023-07-26

### Fixed

-   Use `HOME` environmental variable instead of `USER` to determine home 
    directory. 

## [0.12.2] - 2023-07-25

### Fixed

-   `USER` environmental variable is not present on GitHub Action Runners, so 
    East should not assume that is present.

## [0.12.1] - 2023-06-27

### Fixed

-   Missing sample folder would abort `east release` even if samples are not 
    specified in the `east.yml`.

## [0.12.0] - 2023-06-07

### Added

-   Added `--speed` flag to the `east util connect`. 

## [0.11.1] - 2023-06-05

### Fixed

-   nrfutil toolchain manager binary now needs --ncs-version flag when 
    installing toolchains.

## [0.11.0] - 2023-06-05

### Changed

-   Updated version of the nrfutil toolchain manager binary to 0.13.0-alpha.3. 
    This version now supports toolchains up to v2.4.0. 

### Fixed

-   Completely remove `ncs_version_installed` variable that should be removed 
    in previous version but it was not.

## [0.10.1] - 2023-05-29

### Changed

-   Refactor preworkspace check to improve clarity.
-   Unify helper functions in build type and release tests.

### Fixed

-   A bug that caused a crash when east was run from non-NCS projects.
-   The wrong selection of release binaries when building application with only
    TFM or SPM (#62)

## [0.10.0] - 2023-03-28

### Added

-   Support for Python 3.10.x version.

## [0.9.0] - 2023-03-27

### Added

-   `util rtt` command now supports `--logfile` with which you can specify file
    into which to store RTT logs (#42).
-   `debug` command which uses `west debug` or (`west attach`) to connect to the
    board and start a debugging session.

### Changed

-   Add back functionality to provide `cmake_args` after `--` marker for `build`
    command. Now it is possible to provide custom `-D` define values to the CMake.
    Commands `flash`, `bypass` already provided option for extra arguments after
    `--`, however they did it incorrectly for very edge cases, as they removed
    double quotes from all arguments passed after `--` marker (#56).

### Fixed

-   Ton of spelling mistakes in the code and comments.

## [0.8.0] - 2023-03-20

### Added

-   `compile_commands.json` is now also copied to the top west directory. This
    enables clangd to work as intended in `ncs` and `zephyr` folders (#53).
-   Section in docs/configuration.md document describing `release` build type.

### Changed

-   Samples (which inherently do not have a build type) have their build type
    marked with forward slash "/" instead of "None" in the Job table that appears
    when running `east release` (#52).

### Fixed

-   Sample binaries had incorrect `-None` build type qualifier in their release
    name, when they shouldn't have. Incorrect build type qualifier was removed
    (#52).
-   Samples can now inherit from `release` build types (#47).
-   `east release` command now correctly copies build artefacts when `merged.hex`
    is not generated. Additionally, new _Copied build artefacts_ section in
    `docs/configuration.md` now exactly defines which build artefacts are copied
    and renamed in release procedure (#51).

## [0.7.0] - 2023-02-15

### Added

-   New documentation files in `docs` folder: `development_guide.md`,
    `getting_started.md`, `how_east_works.md`
-   `make format` command, which uses `black` and `isort`. `development_guide.md`
    explains the use.
-   Both commands `east util connect` and `east util rtt` now accept `--rtt-port`
    option, which sets the RTT Telnet port. Command `east util connect` now also
    accepts the `--jlink-id` option, same as `east flash`. With those new options
    is now easier to connect and listen to RTT messages from multiple JLink
    devices.

### Changed

-   Updated readme so it points to the new documentation.

### Fixed

-   Fixed release artefacts naming issue where build type would not appear
    correctly.
-   Create a `release_dry_run` folder instead of release folder when using
    \--dry-run option with _east release_ command.
-   `east release` command now runs a pre-check on the apps and samples from
    `east.yml`, if they exists before running the release process. That way you
    can catch a typo, or a mistake before you spent some time waiting through the
    release process.

## [0.6.2] - 2022-12-16

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

[Unreleased]: https://github.com/IRNAS/irnas-east-software/compare/v0.16.3...HEAD

[0.16.3]: https://github.com/IRNAS/irnas-east-software/compare/v0.16.1...v0.16.3

[0.16.1]: https://github.com/IRNAS/irnas-east-software/compare/v0.16.0...v0.16.1

[0.16.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.15.2...v0.16.0

[0.15.2]: https://github.com/IRNAS/irnas-east-software/compare/v0.15.1...v0.15.2

[0.15.1]: https://github.com/IRNAS/irnas-east-software/compare/v0.15.0...v0.15.1

[0.15.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.14.0...v0.15.0

[0.14.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.13.0...v0.14.0

[0.13.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.12.3...v0.13.0

[0.12.3]: https://github.com/IRNAS/irnas-east-software/compare/v0.12.2...v0.12.3

[0.12.2]: https://github.com/IRNAS/irnas-east-software/compare/v0.12.1...v0.12.2

[0.12.1]: https://github.com/IRNAS/irnas-east-software/compare/v0.12.0...v0.12.1

[0.12.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.11.1...v0.12.0

[0.11.1]: https://github.com/IRNAS/irnas-east-software/compare/v0.11.0...v0.11.1

[0.11.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.10.1...v0.11.0

[0.10.1]: https://github.com/IRNAS/irnas-east-software/compare/v0.10.0...v0.10.1

[0.10.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.9.0...v0.10.0

[0.9.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.8.0...v0.9.0

[0.8.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.7.0...v0.8.0

[0.7.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.6.2...v0.7.0

[0.6.2]: https://github.com/IRNAS/irnas-east-software/compare/v0.6.1...v0.6.2

[0.6.1]: https://github.com/IRNAS/irnas-east-software/compare/v0.6.0...v0.6.1

[0.6.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.5.0...v0.6.0

[0.5.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.4.0...v0.5.0

[0.4.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.3.0...v0.4.0

[0.3.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.2.0...v0.3.0

[0.2.0]: https://github.com/IRNAS/irnas-east-software/compare/v0.1.42...v0.2.0

[0.1.42]: https://github.com/IRNAS/irnas-east-software/compare/5a4f734ca077a91cc2c77b42080f0c9814a489ed...v0.1.42
