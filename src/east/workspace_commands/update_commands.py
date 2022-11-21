import shutil

import click

from ..east_context import east_command_settings, east_group_settings


@click.command(**east_command_settings)
@click.pass_obj
def env(east):
    """Update env"""
    pass


ncs_installed_msg = """Correct version of [bold cyan]NCS[/] toolchain is [bold]already[/] installed!

You can reinstall it with [bold cyan]--force[/] flag.
"""


@click.command(**east_command_settings)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Reinstall the toolchain, even if it is already installed.",
)
@click.pass_obj
def toolchain(east, force):
    """Update NCS toolchain for the current West workspace.

    Determines the version of the NCS that is being used in the current West
    workspace and downloads the correct version of the toolchain for it.

    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """

    east.pre_workspace_command_check(
        ignore_uninstalled_ncs=True,
        ignore_unsupported_ncs=False,
    )

    # We come to here if the detected ncs version is supported
    if east.ncs_version_installed:
        if force:
            shutil.rmtree(
                f"{east.consts['east_dir']}/toolchain/{east.detected_ncs_version}"
            )
        else:
            east.print(ncs_installed_msg)
            east.exit()

    east.print(
        "Starting install of [bold cyan]NCS[/] toolchain,"
        f" version [bold]{east.detected_ncs_version}[/], this will take some time...\n",
        highlight=False,
    )
    east.run_manager(f"install {east.detected_ncs_version}")

    east.print("\n[bold green]Done!")


@click.command(**east_command_settings)
@click.pass_obj
def west(east):
    """Update west"""
    pass


@click.group(**east_group_settings, subcommand_metavar="Subcommands")
@click.pass_obj
def update(east):
    """Command with several subcommands related to updating things."""
    pass


# update.add_command(env)
update.add_command(toolchain)
# update.add_command(west)
