import os
import shutil as sh

import click

from ..east_context import east_command_settings
from ..helper_functions import clean_up_extra_args
from .build_type_flag import construct_extra_cmake_arguments


@click.command(**east_command_settings)
@click.pass_obj
def clean(east):
    """Clean the build folder in current directory.



    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check()

    east.run("rm -fr build")


@click.command(**east_command_settings)
@click.option("-b", "--board", type=str, help="West board to build for.")
@click.option(
    "-u",
    "--build-type",
    type=str,
    help=(
        "Which build type (a group of [bold]Kconfig[/] fragment files) to use. Requires"
        " [bold yellow]east.yml[/] with possible build types."
    ),
)
@click.option(
    "-d",
    "--build-dir",
    type=str,
    help=(
        "Build directory to create or use. If the --build-dir directory is not set, the"
        " default is [bold]build[/] unless the build.dir-fmt configuration variable is"
        " set. The current directory is checked after that. If either is a Zephyr build"
        " directory, it is used. "
    ),
)
@click.option("-t", "--target", type=str, help="Run this build system target.")
@click.argument("cmake-args", nargs=-1, type=str, metavar="-- [cmake-args]")
@click.option(
    "-s",
    "--source-dir",
    type=str,
    help=(
        "Relative path to a directory that should be used as application source"
        " directory."
    ),
)
@click.pass_obj
def build(east, board, build_type, build_dir, target, source_dir, cmake_args):
    """
    Build firmware in the current directory.

    \b
    \n\nInternally runs [magenta bold]west build[/] command in current directory if --source-dir is not set.

    \n\nTo pass additional arguments to the [bold]CMake[/] invocation performed by the [magenta
    bold]west build[/], pass them after a [bold white]"--"[/] at the end of the command line.

    \n\n[bold]Important:[/] Passing additional [bold]CMake[/] arguments like this forces [magenta
    bold]west build[/] to re-run [bold]CMake[/], even if a build system has already been generated.

    For additional info see chapter [bold]Building, Flashing and Debugging[/], section
    [bold]One-Time CMake Arguments[/].

    \n\n[bold]Note:[/] This command will, after build step, copy
    [bold]compile_commands.json[/], if found, from the build directory to the project and top west directory. This makes job of locating this file easier for [bold yellow]clangd[/].

    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """

    east.pre_workspace_command_check()

    build_cmd = create_build_command(
        east, board, build_type, build_dir, target, source_dir, cmake_args
    )

    east.run_west(build_cmd)

    compile_file = os.path.join("build", "compile_commands.json")
    if os.path.isfile(compile_file):
        sh.copyfile(
            compile_file, os.path.join(east.project_dir, "compile_commands.json")
        )
        sh.copyfile(
            compile_file, os.path.join(east.west_dir_path, "compile_commands.json")
        )


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


@click.command(**east_command_settings)
@click.option("-d", "--build-dir", type=str, help="Build directory to create or use.")
@click.option(
    "-r", "--runner", type=str, help="Override default runner from --build-dir."
)
@click.option(
    "-v",
    "--verify",
    is_flag=True,
    help=(
        "Verify, after flash, that contents of the boards code memory regions are the"
        " same as in flashed image."
    ),
)
@click.option(
    "-i",
    "--jlink-id",
    type=str,
    help=(
        "Identification number of a JLink programmer that should be used for flashing."
    ),
)
@click.argument("extra-args", nargs=-1, type=str, metavar="-- [extra args]")
@click.pass_obj
def flash(east, build_dir, runner, verify, jlink_id, extra_args):
    """
    Flash binary to the board's flash.

    \b
    \n\nInternally runs [magenta bold]west flash[/] command. If the build directory is not given, the default is build/ unless the build.dir-fmt configuration variable is set. The current directory is checked after that. If either is a Zephyr build directory, it is used. If there are more than one JLinks connected to the host machine use --jlink-id flag to specify which one to use to avoid selection prompt.

    \n\nTo pass additional arguments to the [bold cyan]runner[/] used by the [magenta
    bold]west flash[/], pass them after a [bold white]"--"[/] at the end of the command line.



    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check()

    flash_cmd = "flash "

    if build_dir:
        flash_cmd += f"-d {build_dir} "
    if runner:
        flash_cmd += f"-r {runner} "

    if verify:
        flash_cmd += "--verify "
    if jlink_id:
        flash_cmd += f"-i {jlink_id} "
    if extra_args:
        flash_cmd += f" {clean_up_extra_args(extra_args)}"

    east.run_west(flash_cmd)


@click.command(**east_command_settings)
@click.option(
    "-s",
    "--shell",
    is_flag=True,
    help=(
        "Launch a sub-shell within the current terminal inside the isolated "
        "environment provided by the [magenta bold]Nordic's nRF Toolchain Manager[/]. "
        "Commands after [bold]--[/] are ignored. To exit the sub-shell type "
        "[bold]exit[/] into it and hit ENTER."
    ),
)
@click.argument("args", nargs=-1, type=str, metavar="-- [args]")
@click.pass_obj
def bypass(east, shell, args):
    """
    Bypass any set of commands directly to the [magenta bold]Nordic's nRF Toolchain Manager[/].

    \b
    \n\nPassing any set of commands after double dash [bold]--[/] will pass them directly to
    the [bold magenta]Nordic's nRF Toolchain Manager[/] executable.

    \n\nThose commands will run in the context of the isolated environment, which is provided by the executable.

    \n\nExample:

    \n\nCommand [bold]east bypass -- west build -b nrf52840dk_nrf52840[/]
    \n\nbecomes [bold]west build -b nrf52840dk_nrf52840[/]



    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check()

    if shell:
        east.enter_manager_shell()
        east.exit(return_code=0)

    if not args:
        east.exit()

    if east.use_toolchain_manager:
        cmd = clean_up_extra_args(args)
        east.run_cmd_in_manager(cmd)
    else:
        east.exit("Toolchain manager is not available in this West workspace.")


@click.command(**east_command_settings)
@click.pass_obj
@click.option(
    "-t",
    "--tui",
    is_flag=True,
    help="If given GDB uses Text User Interface",
)
@click.option(
    "-a",
    "--attach",
    is_flag=True,
    help=(
        "If given only connect to the board and start a debugging session, skip "
        "flashing (uses [bold magenta]west attach[/] instead of [bold magenta]west "
        "debug[/])."
    ),
)
@click.argument("extra_args", nargs=-1, type=str, metavar="-- [args]")
def debug(east, tui, attach, extra_args):
    """Connect to the board, flash the program, and start a debugging session.

    \b
    \n\nPassing any set of commands after double dash [bold]--[/] will pass them directly to
    the [bold magenta]west[/] tool (run east debug -- --help to see all possible options).


    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check()

    cmd = "attach " if attach else "debug "

    if tui:
        cmd += "--tui "

    if extra_args:
        cmd += f"{clean_up_extra_args(extra_args)} "

    east.run_west(cmd)


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
