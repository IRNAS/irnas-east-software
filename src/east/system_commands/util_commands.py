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
@click.option(
    "-p",
    "--rtt-port",
    type=int,
    default=19021,
    help=("Sets the RTT Telnet port. Default: 19021."),
)
@click.option(
    "-s",
    "--speed",
    type=str,
    default=4000,
    help=(
        "Sets the connection speed, can be a number, 'auto' or 'adaptive'. "
        "Default: '4000'."
    ),
)
@click.pass_obj
def connect(east, device, jlink_id, rtt_port, speed):
    """Connects to a device and creates a RTT server with [bold cyan]JLinkExe[/].


    \b
    \n\nRTT server will emit any RTT messages produced by the device over its dedicated port. Execute [bold magenta]east util rtt[/] command in the separate window to observe these messages.

    """

    if not east.check_exe("JLinkExe"):
        east.print(no_jlink_tool_msg("JLinkExe"), highlight=False)
        east.exit()

    cmd = f"JLinkExe -AutoConnect 1 -Speed {speed} -If SWD -RTTTelnetPort {rtt_port} "

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
@click.option(
    "-p",
    "--rtt-port",
    type=int,
    default=19021,
    help=("Sets the RTT Telnet port. Default: 19021."),
)
@click.option(
    "-l",
    "--logfile",
    type=str,
    help="Relative path to a log file into which to save RTT output.",
)
@click.option(
    "-a",
    "--append",
    type=str,
    help="Appends RTT output to a log file, instead of overwriting it. Requires --logfile option.",
)
@click.pass_obj
def rtt(east, local_echo, rtt_port, logfile, append):
    """Runs a RTT client which connects to a running RTT server.


    \b
    \n\nAny messages that RTT server creates are printed. RTT server can be created with an [bold magenta]east util connect[/] command.
    """

    if not east.check_exe("JLinkRTTClient"):
        east.print(no_jlink_tool_msg("JLinkRTTClient"), highlight=False)
        east.exit()

    local_echo = "On" if local_echo else "Off"

    rtt_cmd = f"JLinkRTTClient -LocalEcho {local_echo} -RTTTelnetPort {rtt_port} "

    if logfile and append:
        rtt_cmd += f"ansi2txt | tee -a {logfile}"
    elif logfile:
        rtt_cmd += f"ansi2txt | tee {logfile}"
    elif append:
        east.print(
            "Cannot use [bold cyan]--append[/] flag without "
            "[bold cyan]--logile[/] flag."
        )
        east.exit()

    east.run(rtt_cmd)


@click.group(**east_group_settings, subcommand_metavar="Subcommands")
@click.pass_obj
def util(_):
    """Command with several subcommands related to utilities."""
    pass


util.add_command(connect)
util.add_command(rtt)
