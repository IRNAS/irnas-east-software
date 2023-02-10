# East - tool for building NCS/Zephyr applications

East is a command line meta-tool, useful for creating, managing, and deploying
[Zephyr] or [nRF Connect SDK] (NCS) projects.

[zephyr]: https://docs.zephyrproject.org/latest/
[nrf connect sdk]:
  https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/introduction.html

It is built on top of Zephyr's RTOS meta-tool [West] and Nordic's [nRF Connect
Toolchain Manager].

[west]: https://github.com/zephyrproject-rtos/west
[nrf connect toolchain manager]:
  https://github.com/NordicSemiconductor/pc-nrfconnect-toolchain-manager

## Reasoning behind East

There are several reasons why someone would like to create yet another tool on
top of `west`:

- Working on several projects at once means using different versions of the NCS
  repository and different versions of the toolchain. Managing these differences
  is not a trivial task.
- There is no reproducible build guarantee between the developer's machines.
  Slight differences between tool versions can manifest into hard-to-find bugs.
- Creating GitHub releases manually takes ages as you have to run the build
  process for every combination of the board, application, build variant, etc.
  and properly rename the release binary. The release procedure gets longer with
  every addition of new hardware and build variation option.

East automates the above tasks and tries to make the developer more productive.

## Key features

- Automated detection and installation of tooling required for NCS projects.
- Common `west` commands used for the development, such as `build`, `flash`,
  etc.
- Sandboxed development environment, thanks to the nRF Connect Toolchain
  Manager, every `build`, `flash`, etc. command runs inside of its toolchain
  environment.
- Automated process of generating release artefacts for your entire project, no
  matter the number of applications, samples or boards.
- Support for build types, which is integrated into the usual build process.
- RTT utility commands to connect and see the RTT stream.

## Documentation

`docs` directory contains several markdown documents about East:

- [Getting stared] - Quickly setup an example project and get it building with
  East.
- [How East works] - How East works under the hood and what to expect from it.
- [Configuration] - How to configure build types and release procedure via
  `east.yml` file.
- [Development guide] - How to setup development environment for working on
  East.

[getting stared]: docs/getting_started.md
[how east works]: docs/how_east_works.md
[configuration]: docs/configuration.md
[development guide]: docs/development_guide.md
