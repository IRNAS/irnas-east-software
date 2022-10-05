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
def build(east, board, build_dir, target, source_dir):
    """
    Build firmware in current directory.

    Internally runs [magenta bold]west build[/] command in current directory if --source-dir is set. If the --build-dir directory is not set, the default is build/ unless the build.dir-fmt configuration variable is set. The current directory is checked after that. If either is a Zephyr build directory, it is used.

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
@click.pass_obj
def flash(east, build_dir, runner, verify, jlink_id):
    """
    Flash binary to the board's flash.

    Internally runs [magenta bold]west flash[/] command. If the build directory is not given, the default is build/ unless the build.dir-fmt configuration variable is set. The current directory is checked after that. If either is a Zephyr build directory, it is used. If there are more than one JLinks connected to the host machine use --jlink-id flag to specify which one to use to avoid selection prompt.



    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check()

    flash_cmd = "flash "

    if build_dir:
        flash_cmd += f"-d {build_dir} "
    if runner:
        flash_cmd += f"-r {runner} "

    # Some flags need to be passed as extra parameters to the west tool
    if verify or jlink_id:
        flash_cmd += "-- "

    if verify:
        flash_cmd += "--verify"
    if jlink_id:
        flash_cmd += f"-i {jlink_id}"

    east.run_west(flash_cmd)
