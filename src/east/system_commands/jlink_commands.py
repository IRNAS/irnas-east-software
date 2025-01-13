import click

from ..east_context import east_command_settings
from ..helper_functions import get_device_in_runner_yaml, get_jlink_speed_in_runner_yaml


def no_jlink_tool_msg(tool):
    """Return a message that a required JLink tool was not found."""
    return (
        f"The required program [bold cyan]{tool}[/] was [bold red]not found,[/]"
        " exiting!"
    )


def fmt_runner_error_msg(flag, exception_msg):
    """Format error message for EastJlinkDeviceLoadError."""
    return (
        f"An [bold red]error[/] occurred when trying to extract [bold cyan]{flag}[/] "
        "flag from [bold yellow]runners.yaml[/] file!\n\n"
        f"[italic yellow]{exception_msg}[/]\n"
    )


@click.command(**east_command_settings)
@click.option(
    "-d",
    "--build-dir",
    type=str,
    default="build",
    help=("Build directory of the project. Default: build."),
)
@click.option(
    "-d",
    "--device",
    type=str,
    help=(
        "Set the target device, required by JLinkExe, i.e. [bold]NRF52840_xxAA[/]. "
        "If not given, east tries to infer the device by looking into --build-dir."
    ),
)
@click.option(
    "-i",
    "--dev-id",
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
    help=("Set the RTT Telnet port. Default: 19021."),
)
@click.option(
    "-s",
    "--speed",
    type=str,
    help=(
        "Set the connection speed, can be a number, 'auto' or 'adaptive'. "
        "If not given, east tries to infer the speed by looking into --build-dir."
    ),
)
@click.pass_obj
def connect(east, device, dev_id, rtt_port, speed, build_dir):
    """Connect to a device and create a RTT server with [bold cyan]JLinkExe[/].

    \b
    \n\nRTT server will emit any RTT messages produced by the device over its dedicated port. Execute [bold magenta]east util rtt[/] command in the separate window to observe these messages.

    """
    if not east.check_exe("JLinkExe"):
        east.print(no_jlink_tool_msg("JLinkExe"), highlight=False)
        east.exit()

    cmd = f"JLinkExe -AutoConnect 1 -If SWD -RTTTelnetPort {rtt_port} "

    if dev_id:
        cmd += f"-USB {dev_id} "

    if not device:
        try:
            device = get_device_in_runner_yaml(build_dir)
        except Exception as msg:
            east.print(fmt_runner_error_msg("--device", msg), highlight=False)
            east.exit()

    cmd += f"-Device {device} "

    if not speed:
        try:
            speed = get_jlink_speed_in_runner_yaml(build_dir)
            if not speed:
                speed = 4000
                east.print(
                    f"No --speed param found in runner.yml, falling back to {speed}",
                    highlight=False,
                )
        except Exception as msg:
            east.print(fmt_runner_error_msg("--speed", msg), highlight=False)
            east.exit()

    cmd += f"-Speed {speed} "

    east.run(cmd)


@click.command(**east_command_settings)
@click.option(
    "-e",
    "--local-echo",
    is_flag=True,
    help="Turn on local echo.",
)
@click.option(
    "-p",
    "--rtt-port",
    type=int,
    default=19021,
    help=("Set the RTT Telnet port. Default: 19021."),
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
    help="Append RTT output to a log file, instead of overwriting it. Requires --logfile option.",
)
@click.pass_obj
def rtt(east, local_echo, rtt_port, logfile, append):
    """Run a RTT client and connect a running RTT server.

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
