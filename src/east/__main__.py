import click
import rich_click

from .east_context import EastContext, east_group_settings
from .system_commands import connect, init, install, rtt, update
from .workspace_commands import (
    attach,
    build,
    bypass,
    clean,
    codechecker,
    cortex_debug,
    debug,
    flash,
    release,
    twister,
)

rich_click.rich_click.MAX_WIDTH = 80
rich_click.rich_click.USE_RICH_MARKUP = True
rich_click.rich_click.STYLE_HELPTEXT = "italic dim"

rich_click.rich_click.COMMAND_GROUPS = {
    "east": [
        {
            "name": "Workspace commands",
            "commands": [
                "build",
                "flash",
                "clean",
                "debug",
                "attach",
                "bypass",
                "release",
                "twister",
                "codechecker",
            ],
        },
        {
            "name": "System commands",
            "commands": ["init", "update", "install", "util"],
        },
    ],
    "east update": [{"name": "Subcommands", "commands": ["west", "env", "toolchain"]}],
    "east util": [
        {"name": "Subcommands", "commands": ["connect", "rtt", "cortex-debug"]}
    ],
    "east install": [
        {
            "name": "Packages",
            "commands": ["nrfutil-toolchain-manager", "codechecker", "toolchain"],
        }
    ],
    "east codechecker": [
        {
            "name": "Subcommands",
            "commands": [
                "check",
                "fixit",
                "example-config",
                "store",
                "servdiff",
                "bypass",
            ],
        }
    ],
}


@click.group(**east_group_settings, subcommand_metavar="Subcommands")
@click.pass_obj
def util(_):
    """Command with several subcommands related to utilities."""
    pass


util.add_command(connect)
util.add_command(rtt)
util.add_command(cortex_debug)


@click.group(
    **east_group_settings,
    chain=False,
    subcommand_metavar="<command> [command options]",
)
@click.version_option(message="%(version)s", package_name="east-tool")
@click.option(
    "--echo", is_flag=True, help="Echo each shell command before executing it."
)
@click.pass_context
def cli(ctx, echo):
    """[bold]East[/] is a command line meta-tool, useful for creating, managing and
    deploying [bold cyan]nRF Connect SDK[/] projects.

    \b
    \n\nWant to learn what each command does?

    Run [bold]east \\[command] --help[/] to show documentation for that command.

    \b
    \n\nNote that commands are split into two groups:

    - [bold]Workspace:[/] Can only be run from inside of [bold yellow]West workspace[/].

    - [bold]System:[/] Can be run from anywhere.
    """
    # EastContext object is passed to other subcommands due to the @click.pass_context
    # decorator. Additionally, the subcommands need to be decorated with @click.pass_obj
    # so they directly access the EastContext object.
    ctx.obj = EastContext(echo)
    pass


cli.add_command(build)
cli.add_command(bypass)
cli.add_command(flash)
cli.add_command(clean)
cli.add_command(init)
cli.add_command(update)
cli.add_command(install)
cli.add_command(util)
cli.add_command(release)
cli.add_command(debug)
cli.add_command(attach)
cli.add_command(twister)
cli.add_command(codechecker)


def main():
    """Main entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
