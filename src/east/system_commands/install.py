import os

import click

from ..east_context import east_command_settings, east_group_settings
from ..helper_functions import configure_nrfutil
from .tooling import tool_installer


@click.command(**east_command_settings)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Reinstall the toolchain, even if it is already installed.",
)
@click.pass_obj
def toolchain(east, force):
    """Install NCS toolchain for the current West workspace.

    \b
    \n\nDetermines the version of the NCS that is being used in the current West
    workspace and downloads the correct version of the toolchain for it.

    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check(
        ignore_uninstalled_ncs=True,
        ignore_unsupported_ncs=False,
    )

    # # We come to here if the detected ncs version is installed.
    if east.detected_ncs_version_installed:
        if os.environ.get("EAST_NRFUTIL_CI_MODE", "0") == "1":
            east.print(
                "[bold cyan]EAST_NRFUTIL_CI_MODE[/] is set, NCS toolchain should be "
                "provided by the CI environment, skipping installation."
            )
            east.exit(0)

        if not force:
            msg = (
                f"\nVersion of [bold cyan]{east.detected_ncs_version} NCS[/] toolchain "
                "is [bold]already[/] installed!\n\n"
                "You can reinstall it with [bold cyan]--force[/] flag. "
            )
            east.print(msg)

            # Exit with 0 error code, we do that so it makes usage of East in CI easier.
            east.exit(0)

        east.run_manager(f"uninstall --ncs-version {east.detected_ncs_version}")
        # Empty line for nicer output
        east.print()

    east.print(
        "Starting install of [bold cyan]NCS[/] toolchain,"
        f" version [bold]{east.detected_ncs_version}[/], this will take some time...\n",
        highlight=False,
    )
    east.run_manager(f"install --ncs-version {east.detected_ncs_version}")

    east.print("\n[bold green]Done!")


@click.command(**east_command_settings)
@click.pass_obj
def nrfutil_toolchain_manager(east):
    """Install and configure [bold magenta]nrfutil toolchain-manager[/].

    \b
    \n\nIf [bold]EAST_NRFUTIL_CI_MODE[/] is set to [bold]1[/], this command
    doesn't do anything.
    """
    if os.environ.get("EAST_NRFUTIL_CI_MODE", "0") == "1":
        east.print(
            "[bold cyan]EAST_NRFUTIL_CI_MODE[/] is set, skipping nrfutil "
            "installation and configuration."
        )
        return

    # Environment doesn't provide nrfutil, so we need to download and install
    # in. Below function will just install the nrfutil binary if it is missing.
    tool_installer(east, ["nrfutil"])

    # Configure nrfutil, check for versions and install commands.
    configure_nrfutil(east)


@click.command(**east_command_settings)
@click.pass_obj
def codechecker(east):
    """Install [bold magenta]CodeChecker[/] and its dependencies.

    \b
    \n\nCurrent dependencies are [bold cyan]clang-tidy[/] and [bold cyan]clang[/], both are contained in the [bold cyan]clang+llvm[/] package.
    """
    tool_installer(east, ["codechecker", "clang+llvm", "cppcheck"])


@click.option(
    "--all",
    is_flag=True,
    help="Install all packages.",
)
@click.group(
    **east_group_settings,
    subcommand_metavar="package_name",
    invoke_without_command=True,
)
@click.pass_obj
@click.pass_context
def install(ctx, east, all):
    """Install one or more tools.

    \b
    \n\nTools are always installed in the [bold magenta]~/.local/share/east/tooling[/] directory.

    \n\nTo install a single tool run [bold cyan]east install tool_name[/].
    \n\nTo install all tools run [bold cyan]east install --all[/].
    \n\nTo learn more about a tool run [bold cyan]east install tool_name --help[/].

    """
    # Since we want to call commands in code and not through cli, we need to use
    # .callback method which is actually the original function without click's
    # infrastructure.
    # WARN: There is a better way to do this: invoke method

    if not all and ctx.invoked_subcommand is None:
        east.print(ctx.get_help())
        east.exit(0)

    if all:
        tool_installer(east, ["codechecker", "clang+llvm", "nrfutil"])
        configure_nrfutil(east)
        ctx.invoke(toolchain)


install.add_command(toolchain)
install.add_command(codechecker)
install.add_command(nrfutil_toolchain_manager)
