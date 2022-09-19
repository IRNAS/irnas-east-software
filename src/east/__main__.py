import click

import rich_click
import os
import subprocess

rich_click.rich_click.MAX_WIDTH = 80
rich_click.rich_click.USE_RICH_MARKUP = True
# rich_click.rich_click.STYLE_HELPTEXT = ""


class EastContext:
    """Context-aware API wrapper & state-passing object.

    EastContext object needs to be created in the top level cli command that groups all
    other commands. That object then needs to be passed to every other subcommand.

    Specifically, the class offers wrappers for core API calls (such as `.run`)
    which take into account CLI parser flags, configuration files, and/or
    changes made at runtime.
    """

    def __init__(self, echo: bool = False):
        """Create a new context object.

        Args:
            echo (bool): If True `.run` prints the command string to local stdout prior
            to executing it. Default: ``False``.
        """
        self.cwd = os.getcwd()
        self.echo = echo

    def run(self, command: str):
        """
        Executes given command in shell as a process. This is a blocking call, process
        needs to finish before this command can return;

        Args:
            command (str):  Command to execute.
        """
        if self.echo:
            click.echo(command)

        subprocess.run(command, shell=True)

    def run_west(self, west_command: str):
        """Run wrapper which should be used when executing commands with west tool.

        Args:
            west_command (str):    west command to execute
        """
        self.run("west " + west_command)


@click.command(cls=rich_click.RichCommand, options_metavar="[options]")
@click.pass_obj
def clean(east):
    """Clean the build folder in current directory."""
    east.run("rm -fr build")


@click.command(cls=rich_click.RichCommand, options_metavar="[options]")
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

    [italic]Internally runs [magenta bold]west build[/] command in current directory if
    --source-dir is set. If the --build-dir directory is not set, the default is build/
    unless the build.dir-fmt configuration variable is set. The current directory is
    checked after that. If either is a Zephyr build directory, it is used.[/]
    """

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


flash_help_string = ""


@click.command(
    cls=rich_click.RichCommand,
    options_metavar="[options]",
)
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
    is_flag=True,
    help=(
        "Identification number of a JLink programmer that should be used for flashing."
    ),
)
@click.pass_obj
def flash(east, build_dir, runner, verify, jlink_id):
    """
    Flash binary to the board's flash.

    [italic]Internally runs [magenta bold]west flash[/] command. If the build directory
    is not given, the default is build/ unless the build.dir-fmt configuration variable
    is set. The current directory is checked after that. If either is a Zephyr build
    directory, it is used. If there are more than one JLinks connected to the host
    machine use --jlink-id flag to specify which one to use to avoid selection
    prompt.[/]
    """

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


@click.group(
    cls=rich_click.RichGroup,
    chain=True,
    options_metavar="[options]",
    subcommand_metavar="<command> [command options]",
)
@click.version_option(message="%(version)s", package_name="east-tool")
@click.option(
    "--echo", is_flag=True, help="Echo each shell command before executing it."
)
@click.pass_context
def cli(ctx, echo):
    """
    [bold]East[/] is a command line meta-tool, usefull for creating, managing and
    deploying [bold cyan]nRF Connect SDK[/] projects.

    \b
    \n\n[italic]Want to learn what each command does?

    Run [bold]east \[command] --help[/] to show documentation for that command.[/]
    """

    # EastContext object is passed to other subcommands due to the @click.pass_context
    # decorator. Additionally, the subcommands need to be decorated with @click.pass_obj
    # so they directly access the EastContext object.
    ctx.obj = EastContext(echo)
    pass


cli.add_command(clean)
cli.add_command(build)
cli.add_command(flash)


def main():
    cli()


if __name__ == "__main__":
    main()
