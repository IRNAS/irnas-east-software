import click

from ..east_context import east_command_settings
from ..helper_functions import clean_up_extra_args


@click.command(
    **east_command_settings,
    context_settings=dict(ignore_unknown_options=True, allow_extra_args=True),
)
@click.pass_obj
@click.option(
    "--extra-help",
    is_flag=True,
    help="Print help of the [bold magenta]west init[/] command.",
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED, metavar="")
def init(east, extra_help, args):
    """Create a [bold yellow]West workspace[/].

    \b
    \n\nInternally runs [magenta bold]west init[/] command, all given arguments are passed directly to it.

    \n\nTo learn more about possible [magenta bold]west init[/] arguments and options use --extra-help flag.


    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    cmd = "init "

    if extra_help:
        cmd += "--help"
        east.run_west(cmd)
        east.exit(return_code=0)

    if args:
        cmd += f"{clean_up_extra_args(args)} "

    east.run_west(cmd)


@click.command(
    **east_command_settings,
    context_settings=dict(ignore_unknown_options=True, allow_extra_args=True),
)
@click.pass_obj
@click.option(
    "--extra-help",
    is_flag=True,
    help="Print help of the [bold magenta]west update[/] command.",
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED, metavar="")
def update(east, extra_help, args):
    """Update a [bold yellow]West workspace[/].

    \b
    \n\nInternally runs [magenta bold]west update[/] command, all given arguments are passed directly to it.

    \n\nTo learn more about possible [magenta bold]west update[/] arguments and options use --extra-help flag.


    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    cmd = "update "

    if extra_help:
        cmd += "--help"
        east.run_west(cmd)
        east.exit(return_code=0)

    if args:
        cmd += f"{clean_up_extra_args(args)} "

    east.run_west(cmd)
