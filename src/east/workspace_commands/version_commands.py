import os

import click

from ..east_context import east_command_settings
from ..helper_functions import determine_version_file

version_misuse_no_east_yml_msg = """
[bold yellow]east.yml[/] not found in project's root directory, [bold yellow]east util
version[/] needs it to determine VERSION paths, exiting!"""


@click.command(**east_command_settings)
@click.pass_obj
@click.option(
    "-t",
    "--tag",
    type=str,
    help="The tag to use for version information in the format "
    "v<MAJOR>.<MINOR>.<PATCH>[-<EXTRA>][+<TWEAK>], eg. [bold yellow]v1.2.3[/], "
    "[bold yellow]v1.2.3+4[/] or [bold yellow]v1.2.3-rc1+4[/]. If this flag is given, "
    "the [bold cyan]east util version[/] command assumes that the git HEAD is on the "
    "tagged commit and that the repo is clean.",
)
@click.argument(
    "paths", nargs=-1, type=click.UNPROCESSED, metavar="[PATH1 [PATH2 ...]]"
)
def version(east, tag, paths):
    """Generate Zephyr's [bold white]VERSION[/] files on the given [bold cyan]PATHs[/].

    \b
    \n\nThe command accepts the [bold cyan]PATHs[/] from two sources:

    \b
    \n\n- As positional command line arguments, if provided, e.g., command [bold yellow]east util version app/test_one app/test_two[/] creates [bold white]VERSION[/] files in those directories.\n
    - From [bold yellow]east.yml file[/], if no arguments are not provided, the [bold cyan]PATHs[/] are taken from the [bold magenta]version.paths[/] field in the [bold yellow]east.yml[/] file.\n

    \b
    \n\nExample [bold yellow]east.yml[/]:

    \b\n
    version:\n
    \b\tpaths:\n
    \b\t  - app/test_one\n
    \b\t  - app/test_two\n

    \b
    \n\nRegardless of the source, the [bold cyan]PATHs[/] should always be relative to the project directory.\n

    \b
    \n\nFor version information the output of the [bold cyan]git describe --tags --always --long --dirty=+[/] command is used. Giving the [bold cyan]--tag[/] flag overrides the git command output.
    """
    east.pre_workspace_command_check()

    if not paths:
        if not east.east_yml:
            east.print(version_misuse_no_east_yml_msg)
            east.exit(1)

        if "version" not in east.east_yml:
            msg = (
                "[bold]VERSION[/] files couldn't be created as no paths were given.\n\n"
                "Either provide paths as a positional argument to the "
                "[bold magenta]east util version[/] command or list them under "
                "[bold magenta]version.paths[/] field in "
                "[bold yellow]east.yml[/] file."
            )
            east.print(msg)
            east.exit(1)

        paths = east.east_yml["version"]["paths"]

    # All paths are relative to the project_dir
    paths = [os.path.join(east.project_dir, p) for p in paths]

    for p in paths:
        if not os.path.exists(p):
            msg = f"Can't create [bold]VERSION[/] file on {p}, the path doesn't exist."
            east.print(msg)
            east.exit(1)

    version_file = determine_version_file(east, tag)

    msgs = []
    for p in paths:
        path = os.path.join(p, "VERSION")
        msgs.append(f"{'Overwritten' if os.path.isfile(path) else 'Created'} {path}")

        with open(path, "w") as f:
            f.write(version_file)

    for m in msgs:
        east.print(m)
