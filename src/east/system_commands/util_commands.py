import os

import click
import yaml

from ..east_context import east_command_settings, east_group_settings


def no_jlink_tool_msg(tool):
    return (
        f"The required program [bold cyan]{tool}[/] was [bold red]not found,[/]"
        " exiting!"
    )


def get_device(runner_yaml):
    """Returns device flag for jlink runner from runner.yaml.

    If runner.yaml is not found or the correct flag could not be fetched then None is
    returned.
    """

    if os.path.isfile(runner_yaml):
        with open(runner_yaml, "r") as file:
            try:
                jlink_args = yaml.safe_load(file)["args"]["jlink"]
                device_flag = next(filter(lambda e: "--device" in e, jlink_args))
                return device_flag.split("=")[1]
            except (KeyError, StopIteration):
                pass
    return None


@click.command(**east_command_settings)
@click.option(
    "-d",
    "--device",
    default=get_device(os.path.join("build", "zephyr", "runners.yaml")),
    type=str,
    help=(
        "Sets the target device, required by JLinkExe, i.e. [bold]NRF52840_xxAA[/]. "
        "If not given, east tries to infer the device by looking into Zephyr's build folder."
    ),
)
@click.option(
    "-i",
    "--jlink-id",
    type=int,
    help=(
        "Identification number of a JLink programmer that should be used for connecting."
    ),
)
@click.pass_obj
def connect(east, device, jlink_id):

    """Connects to a device and creates a RTT server with [bold cyan]JLinkExe[/].


    \b
    \n\nRTT server will emmit any RTT messages produced by the device over its dedicated port. Execute [bold magenta]east util rtt[/] command in the separate window to observe these messages.

    """

    if not east.check_exe("JLinkExe"):
        east.print(no_jlink_tool_msg("JLinkExe"), highlight=False)
        east.exit()

    cmd = "JLinkExe -AutoConnect 1 -Speed 4000 -If SWD "

    if jlink_id:
        cmd += f"-USB {jlink_id} "

    if device:
        cmd += f"-Device {device} "

    east.run(cmd)


@click.command(**east_command_settings)
@click.option(
    "-e",
    "--local-echo",
    is_flag=True,
    help="Turns on local echo.",
)
@click.pass_obj
def rtt(east, local_echo):
    """Runs a RTT client which connects to a running RTT server.


    \b
    \n\nAny messages that RTT server creates are printed. RTT server can be created with an [bold magenta]east util connect[/] command.
    """

    if not east.check_exe("JLinkRTTClient"):
        east.print(no_jlink_tool_msg("JLinkRTTClient"), highlight=False)
        east.exit()

    local_echo = "On" if local_echo else "Off"

    east.run(f"JLinkRTTClient -LocalEcho {local_echo}")


@click.group(**east_group_settings, subcommand_metavar="Subcommands")
@click.pass_obj
def util(east):
    """Command with several subcommands related to utilities."""
    pass


util.add_command(connect)
util.add_command(rtt)
