import os
import shutil as sh

import click

from ..east_context import east_command_settings
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
# @click.argument("cmake-args", nargs=-1, type=str, metavar="-- [cmake-args]")
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
def build(east, board, build_type, build_dir, target, source_dir):
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
        east, board, build_type, build_dir, target, source_dir
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
    silence_diagnostic=False,
):
    """Creates build command. This is needed so it can also be reused by release command"""
    build_cmd = "build"

    if board:
        build_cmd += f" -b {board}"
    if build_dir:
        build_cmd += f" -d {build_dir}"
    if target:
        build_cmd += f" -t {target}"
    if source_dir:
        build_cmd += f" {source_dir}"

    # WARN: cmake args are making some problems in this form.
    # if cmake_args:
    #     build_cmd += f" -- \"{' '.join(cmake_args)}\""

    # "release" is an alias for default build type (for both apps and samples).
    # This is here to make the release logic cleaner, and not to further complicate the
    # construct_extra_cmake_arguments, however it should be inside of it.
    if build_type == "release":
        build_type = None

    build_type_args, diagnostic = construct_extra_cmake_arguments(
        east,
        build_type,
        board,
        build_dir,
        source_dir,
    )

    if diagnostic and not silence_diagnostic:
        east.print(diagnostic)

    if build_type_args:
        build_cmd += f" -- {build_type_args}"

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

    # Some flags need to be passed as extra parameters to the west tool
    if verify or jlink_id or extra_args:
        flash_cmd += "-- "

    if verify:
        flash_cmd += "--verify "
    if jlink_id:
        flash_cmd += f"-i {jlink_id} "
    if extra_args:
        flash_cmd += f"\"{' '.join(extra_args)}\" "

    east.run_west(flash_cmd)


@click.command(**east_command_settings)
@click.argument("args", nargs=-1, type=str, metavar="-- [args]")
@click.pass_obj
def bypass(east, args):
    """
    Bypass any set of commands directly to the [magenta bold]west tool[/].

    \b
    \n\nPassing any set of commands after double dash [bold]--[/] will pass them directly to
    the [bold magenta]west[/] tool.

    \n\nExample:

    \n\nCommand [bold]east bypass -- build -b nrf52840dk_nrf52840[/]
    \n\nbecomes [bold]west build -b nrf52840dk_nrf52840[/]



    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check()

    if not args:
        east.exit()

    # Click argument automatically strips double quotes from anything that is given
    # after "--". Double quotes are needed if specifying define values (-D) to the cmake
    # args, below list comprehension adds them back.
    def add_back_double_quotes(arg):
        splited = arg.split("=")
        return f'{splited[0]}="{splited[1]}"'

    args = [add_back_double_quotes(arg) if "=" in arg else arg for arg in args]

    cmd = f"{' '.join(args)} "
    east.run_west(cmd)
