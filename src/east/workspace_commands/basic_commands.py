import argparse
import copy
import os
import re
import shutil as sh

import click
from rich_click.rich_command import RichCommand

from ..east_context import east_command_settings
from ..helper_functions import clean_up_extra_args, find_app_build_dir
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

    build_cmd, opts = create_build_command_from_commandline(east, ctx.raw_args)
    build_dir = opts.build_dir if opts.build_dir else "build"

    if spdx:
        east.run_west(f"spdx --init --build-dir {build_dir}")

    east.run_west(build_cmd)

    if spdx:
        east.run_west(f"spdx --build-dir {build_dir} --analyze-includes --include-sdk")

    compile_file = os.path.join(find_app_build_dir(build_dir), "compile_commands.json")
    if os.path.isfile(compile_file):
        for dest in [east.project_dir, east.west_dir_path]:
            sh.copyfile(compile_file, os.path.join(dest, "compile_commands.json"))

    create_codecheckerfile(east, opts.board, build_type, build_dir, opts.source_dir)


def create_build_command_from_commandline(east, raw_args):
    """Helper for creating a build command.

    It parses raw_args (which is a list) and creates two objects:

        - build_cmd: a string with the build command, intended to be given to run_west()
        - opts: an object with parsed arguments
    """
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-b", "--board")
    parser.add_argument("-d", "--build-dir")
    parser.add_argument("-t", "--target")
    parser.add_argument("-u", "--build-type")
    opts, _ = parser.parse_known_args(raw_args)

    # We need to find source_dir ourselves, ArgumentParser can't find, unless we specify
    # all possible west build arguments.
    source_dir = find_source_dir(raw_args)
    opts.source_dir = source_dir

    # If cmake arguments are present, extract them and remove them from the raw_args.
    cmake_args = None
    if "--" in raw_args:
        # First extract the cmake arguments and then the rest that comes before the
        # "--", order is important.
        cmake_args = clean_up_extra_args(raw_args[raw_args.index("--") + 1 :])
        raw_args = raw_args[: raw_args.index("--")]

    build_type_args, diagnostic = construct_extra_cmake_arguments(
        east,
        opts.build_type,
        opts.board,
        opts.build_dir,
        opts.source_dir,
    )
    if diagnostic:
        east.print(diagnostic)

    # Construct the build command
    build_cmd = ["build"]
    build_cmd += raw_args

    if build_type_args or cmake_args:
        build_cmd.append("--")

        if build_type_args:
            build_cmd.append(build_type_args)

        if cmake_args:
            build_cmd.append(cmake_args)

    # Change list to a string
    build_cmd = " ".join(build_cmd)

    # If --build-type is in raw_args remove it and the following argument. The extra \s*
    # is needed to remove the space after the argument.
    build_cmd = re.sub(r"(-u|--build-type) (\S+)\s*", "", build_cmd).strip()

    return build_cmd, opts


def find_source_dir(raw_args):
    """Helper for finding the source directory in the raw_args."""
    source_dir = None
    is_option_flag = False

    for arg in raw_args:
        if arg == "--":
            break
        if arg.startswith("-"):
            is_option_flag = True
            continue
        elif is_option_flag:
            is_option_flag = False
            continue
        else:
            source_dir = arg
            break

    return source_dir


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
