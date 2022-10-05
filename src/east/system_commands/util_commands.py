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
    type=str,
    help="Selects the target device, required by JLinkExe.",
)
@click.pass_obj
def connect(east, device):
    """Connects to a device and creates a RTT server with [bold cyan]JLinkExe[/].


    \b
    \n\nRTT server will emmit any RTT messages produced by the device over its dedicated port. Execute [bold magenta]east util rtt[/] command in the separate window to observe these messages.

    \n\n[bold]Note:[/] If the current directory contains a Zepyhr's build folder it will
    automatically try to determine the correct target device for [bold cyan]JLinkExe[/] command.
    If there is no build folder and target device can not be determined, then [bold
    cyan]JLinkExe[/] command will give option to select the correct target device.
    \n\nUser can also provide --device option directly, in that case the previously
    described process is skipped.

    """

    if not east.check_exe("JLinkExe"):
        east.print(no_jlink_tool_msg("JLinkExe"), highlight=False)
        east.exit()

    cmd = "JLinkExe -AutoConnect 1 -Speed 4000 -If SWD "

    # Execute early if --device is given
    if device:
        cmd += f"-Device {device}"
        east.run(cmd)

    # Try to determine the device arg from runner.yaml file
    runner_yaml = os.path.join("build", "zephyr", "runners.yaml")
    device_arg = get_device(runner_yaml)

    # Could be None
    if device_arg:
        cmd += f"-Device {device_arg }"

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

    cmd = "JLinkRTTClient "
    if local_echo:
        cmd += "-LocalEcho On"

    east.run(cmd)


@click.group(**east_group_settings, subcommand_metavar="Subcommands")
@click.pass_obj
def util(east):
    """Command with several subcommands related to utilities."""
    pass


util.add_command(connect)
util.add_command(rtt)
