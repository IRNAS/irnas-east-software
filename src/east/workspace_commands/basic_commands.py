import argparse
import copy
import os
import shutil as sh

import click
from rich_click.rich_command import RichCommand

from ..east_context import east_command_settings
from ..helper_functions import clean_up_extra_args
from .build_type_flag import construct_extra_cmake_arguments
from .codechecker_helpers import create_codecheckerfile


@click.command(**east_command_settings)
@click.pass_obj
def clean(east):
    """Clean the build folder in current directory.

    \b
    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check()

    east.run("rm -fr build")


class SpecialCommand(RichCommand):
    """Special command that allows to access the raw args."""

    def parse_args(self, ctx, args):
        """Parse the args and store a copy of them in the context."""
        # Before parsing the args, make a copy of them so they can be used later.
        # This is needed because "--" is silently removed from the args by the click,
        # but it is needed to determine the source dir.
        ctx.raw_args = copy.deepcopy(args)
        return super(SpecialCommand, self).parse_args(ctx, args)


@click.command(
    cls=SpecialCommand,
    options_metavar="[options]",
    context_settings=dict(ignore_unknown_options=True, allow_extra_args=True),
)
@click.option(
    "-u",
    "--build-type",
    type=str,
    help=(
        "Which build type (a group of [bold]Kconfig[/] fragment files) to use. Requires"
        " [bold yellow]east.yml[/] with possible build types with specified apps and "
        "samples."
    ),
)
@click.option(
    "--spdx",
    is_flag=True,
    help=(
        "Create an SPDX 2.2 tag-value bill of materials following the completion "
        "of a Zephyr build."
    ),
)
@click.option(
    "--extra-help",
    is_flag=True,
    help="Print help of the [bold magenta]west build[/] command.",
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED, metavar="")
@click.pass_obj
@click.pass_context
def build(ctx, east, build_type, spdx, extra_help, args):
    """Build firmware in the current directory.

    \b
    \n\nInternally runs [magenta bold]west build[/] command, all given arguments are passed directly to it. To learn more about possible [magenta bold]west build[/] arguments and options use --extra-help flag.


    \n\nAfter the build step, if the file [bold]compile_commands.json[/] is found in build dir it will be copied to the project and top west directory. This makes job of locating this file easier for [bold yellow]clangd[/].


    \n\nTo pass additional arguments to the [bold]CMake[/] invocation performed by the [magenta
    bold]west build[/], pass them after a [bold white]"--"[/] at the end of the command line.

    \n\nIf the source dir is listed in the [bold yellow]east.yml[/] then [bold yellow]build type[/] functionality is enabled. East will add a group of [bold]Kconfig[/] fragment files to the build as specified by the selected build type and [bold yellow]east.yml[/] file. See [bold]docs/configuration.md[/] for more info.

    \n\n[bold]Note:[/] When using build types functionality make sure to not pass CONF_FILE and OVERLAY_CONFIG variables to the [bold]CMake[/].
    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    _ = args

    east.pre_workspace_command_check()

    if extra_help:
        east.run_west("build --help")
        east.exit(return_code=0)

    build_cmd, opts = create_build_command_from_commandline(
        east, ctx.raw_args, build_type
    )
    build_dir = opts.build_dir if opts.build_dir else "build"

    if spdx:
        east.run_west(f"spdx --init --build-dir {build_dir}")

    east.run_west(build_cmd)

    if spdx:
        east.run_west(f"spdx --build-dir {build_dir} --analyze-includes --include-sdk")

    compile_file = os.path.join("build", "compile_commands.json")
    if os.path.isfile(compile_file):
        for dest in [east.project_dir, east.west_dir_path]:
            sh.copyfile(compile_file, os.path.join(dest, "compile_commands.json"))

    create_codecheckerfile(
        east, opts.board, build_type, opts.build_dir, opts.source_dir
    )


def create_build_command_from_commandline(east, raw_args, build_type):
    """Helper for creating a build command.

    It parses raw_args and creates two objects:
    - build_cmd: a string with the build command, intended to be given to run_west()
    - opts: an object with parsed arguments
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-b", "--board")
    parser.add_argument("-d", "--build-dir")
    parser.add_argument("-t", "--target")

    # find source_dir in the args
    source_dir = None
    option_flag = False

    for arg in raw_args:
        if arg == "--":
            break
        if arg.startswith("-"):
            option_flag = True
            continue
        elif option_flag:
            option_flag = False
            continue
        else:
            source_dir = arg
            break

    # find cmake_args in the args
    cmake_args = raw_args[raw_args.index("--") + 1 :] if "--" in raw_args else None

    # Parse the rest of the args
    opts, _ = parser.parse_known_args(raw_args)
    opts.source_dir = source_dir

    build_cmd = create_build_command(
        east,
        opts.board,
        build_type,
        opts.build_dir,
        opts.target,
        source_dir,
        cmake_args,
    )

    return build_cmd, opts


def create_build_command(
    east,
    board=None,
    build_type=None,
    build_dir=None,
    target=None,
    source_dir=None,
    cmake_args=None,
    silence_diagnostic=False,
):
    """Helper for creating a build command. This extra helper is needed so it can also
    be reused by release command.

    Returns:
        build_cmd: a string with the build command, intended to be given to run_west()
    """
    build_type_args, diagnostic = construct_extra_cmake_arguments(
        east,
        build_type,
        board,
        build_dir,
        source_dir,
    )

    if diagnostic and not silence_diagnostic:
        east.print(diagnostic)

    build_cmd = "build"

    if board:
        build_cmd += f" -b {board}"
    if build_dir:
        build_cmd += f" -d {build_dir}"
    if target:
        build_cmd += f" -t {target}"
    if source_dir:
        build_cmd += f" {source_dir}"

    # Some flags need to be passed as extra parameters to the west tool
    if build_type_args or cmake_args:
        build_cmd += " --"

    if build_type_args:
        build_cmd += f" {build_type_args}"

    if cmake_args:
        build_cmd += f" {clean_up_extra_args(cmake_args)}"

    return build_cmd


@click.command(
    **east_command_settings,
    context_settings=dict(ignore_unknown_options=True, allow_extra_args=True),
)
@click.pass_obj
@click.option(
    "--extra-help",
    is_flag=True,
    help="Print help of the [bold magenta]west flash[/] command.",
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED, metavar="")
def flash(east, extra_help, args):
    """Flash binary to the board's flash.

    \b
    \n\nInternally runs [magenta bold]west flash[/] command, all given arguments are passed directly to it.

    \n\nTo learn more about possible [magenta bold]west flash[/] arguments and options use --extra-help flag.


    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check()

    cmd = "flash "

    if extra_help:
        cmd += "--help"
        east.run_west(cmd)
        east.exit(return_code=0)

    if args:
        cmd += f"{clean_up_extra_args(args)} "

    east.run_west(cmd)


@click.command(**east_command_settings)
@click.option(
    "-s",
    "--shell",
    is_flag=True,
    help=(
        "Launch a sub-shell within the current terminal inside the isolated "
        "environment provided by the [magenta bold]nrfutil toolchain-manager[/]. "
        "Commands after [bold]--[/] are ignored. To exit the sub-shell type "
        "[bold]exit[/] into it and hit ENTER."
    ),
)
@click.argument("args", nargs=-1, type=str, metavar="-- [args]")
@click.pass_obj
def bypass(east, shell, args):
    """Bypass any set of commands directly to the [magenta bold]nrfutil toolchain-manager[/].

    \b
    \n\nPassing any set of commands after double dash [bold]--[/] will pass them directly to
    the [bold magenta]nrfutil toolchain-manager[/] executable.

    \n\nThose commands will run in the context of the isolated environment, which is provided by the executable.

    \n\nExample:

    \n\nCommand [bold]east bypass -- west build -b nrf52840dk_nrf52840[/]
    \n\nbecomes [bold]west build -b nrf52840dk_nrf52840[/]



    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check()

    if not east.detected_ncs_version:
        east.print(
            "No version of [bold cyan]nRF Connect SDK[/] was detected in this "
            "[bold yellow]West workspace[/], can't run [bold magenta]east bypass[/]."
        )
        east.exit()

    if shell:
        east.enter_manager_shell()
        east.exit(return_code=0)

    if not args:
        east.exit()

    if not east.use_toolchain_manager:
        east.exit(
            "nrfutil toolchain manager is not available in this [bold yellow]West workspace[/]."
        )

    cmd = clean_up_extra_args(args)
    east.run_cmd_in_manager(cmd)


@click.command(
    **east_command_settings,
    context_settings=dict(ignore_unknown_options=True, allow_extra_args=True),
)
@click.pass_obj
@click.option(
    "--extra-help",
    is_flag=True,
    help="Print help of the [bold magenta]west debug[/] command.",
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED, metavar="")
def debug(east, extra_help, args):
    """Connect to the board, flash the program, and start a debugging session.

    \b
    \n\nInternally runs [magenta bold]west debug[/] command, all given arguments are passed directly to it.

    \n\nTo learn more about possible [magenta bold]west debug[/] arguments and options use --extra-help flag.

    \n\n[bold]Note:[/] Add --tui flag to use Text User Interface.
    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check()

    if extra_help:
        east.run_west("debug --help")
    else:
        east.run_west("debug " + clean_up_extra_args(args), ignore_sigint=True)


@click.command(
    **east_command_settings,
    context_settings=dict(ignore_unknown_options=True, allow_extra_args=True),
)
@click.pass_obj
@click.option(
    "--extra-help",
    is_flag=True,
    help="Print help of the [bold magenta]west attach[/] command.",
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED, metavar="")
def attach(east, extra_help, args):
    """Like "east debug", but doesn't reflash the program.

    \b
    \n\nInternally runs [magenta bold]west attach[/] command, all given arguments are passed directly to it.

    \n\nTo learn more about possible [magenta bold]west attach[/] arguments and options use --extra-help flag.

    \n\n[bold]Note:[/] Add --tui flag to use Text User Interface.
    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check()

    if extra_help:
        east.run_west("attach --help")
    else:
        east.run_west("attach " + clean_up_extra_args(args), ignore_sigint=True)


@click.command(
    **east_command_settings,
    context_settings=dict(ignore_unknown_options=True, allow_extra_args=True),
)
@click.pass_obj
@click.option(
    "--extra-help",
    is_flag=True,
    help="Print help of the [bold magenta]west twister[/] command.",
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED, metavar="")
def twister(east, extra_help, args):
    """Run Twister, a test runner tool.

    \b
    \n\nInternally runs [magenta bold]west twister[/] command, all given arguments are passed directly to it.

    \n\nTo learn more about possible Twister arguments and options use --extra-help flag.


    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check()

    cmd = "twister "

    if extra_help:
        cmd += "--help"
        east.run_west(cmd)
        east.exit(return_code=0)

    if args:
        cmd += f"{clean_up_extra_args(args)} "

    east.run_west(cmd)
