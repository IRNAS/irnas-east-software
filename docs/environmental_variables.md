# Environmental Variables

East can be configured using environmental variables. The following variables are available:

- `EAST_NRFUTIL_CI_MODE`
- `EAST_CODECHECKER_CI_MODE`

All variables are considered to be set if they are defined and set to `1`, otherwise they are
considered to be unset.

## `EAST_NRFUTIL_CI_MODE`

When `EAST_NRFUTIL_CI_MODE` is set, East will use the `nrfutil` binary that is found on the `PATH`.
It expects that the `nrfutil` has the installed both `device` and `toolchain` manager commands. Any
East commands that somehow manage the `nrfutil` tool (e.g. `east install toolchain-manager`) won't
do anything, they will just print a message and exit with a success code.

Additionally, East will assume that it doesn't need to run shell commands through the
`nrfutil toolchain-manager launch` command to get access to various toolchain commands (such as
`python`, C compilers, etc.) . It is expected that all commands are available on the `PATH`.

## `EAST_CODECHECKER_CI_MODE`

When `EAST_CODECHECKER_CI_MODE` is set, East will use the `CodeChecker` binary that is found on the
`PATH`. It expects also expects that various `CodeChecker` analyzers (such as `clangsa` and
`clang-tidy`) are installed and available on the `PATH`. Any East commands that somehow manage the
`CodeChecker` tool (e.g. `east install codecheker`) won't do anything, they will just print a
message and exit with a success code.
