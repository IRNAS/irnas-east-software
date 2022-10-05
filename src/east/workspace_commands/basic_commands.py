import click

from ..east_context import east_command_settings


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
@click.option("-d", "--build-dir", type=str, help="Build directory to create or use.")
@click.option("-t", "--target", type=str, help="Run this build system target.")
@click.argument("cmake-args", nargs=-1, type=str, metavar="-- [cmake-args]")
@click.option(
    "-s",
    "--source-dir",
    type=str,
    help=(
        "Relative path to a directory that should be used as source instead of the"
        " current one."
    ),
)
@click.pass_obj
def build(east, board, build_dir, target, source_dir, cmake_args):
    """
    Build firmware in current directory.

    Internally runs [magenta bold]west build[/] command in current directory if --source-dir is set. If the --build-dir directory is not set, the default is build/ unless the build.dir-fmt configuration variable is set. The current directory is checked after that. If either is a Zephyr build directory, it is used.

    \n\nTo pass additional arguments to the [bold]CMake[/] invocation performed by the [magenta
    bold]west build[/], pass them after a [bold white]"--"[/] at the end of the command line.

    \n\n[bold]Important:[/] Passing additional [bold]CMake[/] arguments like this forces [magenta
    bold]west build[/] to re-run [bold]CMake[/], even if a build system has already been generated.

    For additional info see chapter [bold]Building, Flashing and Debugging[/], section
    [bold]One-Time CMake Arguments[/].



    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """

    east.pre_workspace_command_check()

    build_cmd = "build "

    if board:
        build_cmd += f"-b {board} "
    if build_dir:
        build_cmd += f"-d {build_dir} "
    if target:
        build_cmd += f"-t {target} "
    if source_dir:
        build_cmd += f"{source_dir} "
    if cmake_args:
        build_cmd += f"-- \"{' '.join(cmake_args)}\" "

    east.run_west(build_cmd)


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

    Internally runs [magenta bold]west flash[/] command. If the build directory is not given, the default is build/ unless the build.dir-fmt configuration variable is set. The current directory is checked after that. If either is a Zephyr build directory, it is used. If there are more than one JLinks connected to the host machine use --jlink-id flag to specify which one to use to avoid selection prompt.

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

    Passing any set of commands after double dash [bold]--[/] will pass them directly to
    the [bold magenta]west[/] tool.

    \n\nExample:

    \n\nCommand [bold]east bypass -- build -b nrf52840dk_nrf52840[/]
    \n\nbecomes [bold]west build -b nrf52840dk_nrf52840[/]



    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check()

    if args:
        cmd = f"{' '.join(args)} "
        east.run_west(cmd)
