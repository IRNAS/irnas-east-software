# East - tool for building NCS/Zephyr applications

East is a command line meta-tool, useful for creating, managing, and deploying [Zephyr] or [nRF
Connect SDK] (NCS) projects.

[zephyr]: https://docs.zephyrproject.org/latest/
[nrf connect sdk]: https://developer.nordicsemi.com/nRF_Connect_SDK/doc/latest/nrf/introduction.html

It is built on top of Zephyr's RTOS meta-tool [West] and Nordic's [nRF Connect Toolchain Manager].

[west]: https://github.com/zephyrproject-rtos/west
[nrf connect toolchain manager]:
  https://github.com/NordicSemiconductor/pc-nrfconnect-toolchain-manager

## Documentation

`docs` directory contains several markdown documents about East:

- [Installation] - How to install East and its dependencies.
- [Example Project] - Quickly setup an example project and get it building with East.
- [How East works] - How East works under the hood and what to expect from it.
- [Configuration] - How to configure the `east.yml` file.
- [Pack] - How to use `east pack` command to create a release package.
- [Environmental variables] - How to configure East using environmental variables.
- [Development guide] - How to setup the development environment for working on East.

[installation]: docs/installation.md
[Example Project]: docs/getting_started.md
[how east works]: docs/how_east_works.md
[configuration]: docs/configuration.md
[pack]: docs/pack.md
[environmental variables]: docs/environmental_variables.md
[development guide]: docs/development_guide.md

## Reasoning behind East

There are several reasons why someone would like to create yet another tool on top of `west`:

- Working on several projects at once means using different versions of the NCS repository and
  different versions of the toolchain. Managing these differences is not a trivial task.
- There is no reproducible build guarantee between the developer's machines. Slight differences
  between tool versions can manifest into hard-to-find bugs.
- Creating GitHub releases manually takes ages as you have to run the build process for every
  combination of the board, application, build variant, etc. and properly rename the release binary.
  The release procedure gets longer with every addition of new hardware and build variation option.

East automates the above tasks and tries to make the developer more productive.

## Key features

- Automated detection and installation of tooling required for NCS projects.
- Common `west` commands used for the development, such as `build`, `flash`, etc.
- Sandboxed development environment, thanks to the nRF Connect Toolchain Manager, every `build`,
  `flash`, etc. command runs inside of its toolchain environment.
- Automated process of packaging release artifacts for your entire project.
- RTT utility commands to connect and see the RTT stream.
- CodeChecker integration for static code analysis.
- Generating configuration files for the Cortex Debug VScode extension.
