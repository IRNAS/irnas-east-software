import copy
import json
import os

import click
import rich.prompt

from ..east_context import east_command_settings
from ..helper_functions import determine_svd_file, get_cortex_debug_params


@click.command(**east_command_settings)
@click.pass_obj
@click.option(
    "-d",
    "--build-dir",
    type=str,
    default="build",
    help=("Build directory of the project to debug. Default: build."),
)
@click.option(
    "-r",
    "--rtt-config",
    is_flag=True,
    help=(
        "Add RTT configuration to the launch.json file. With it the Cortex Debug "
        "starts an RTT client in the VSCode. If set then any external RTT clients "
        "won't be able to connect to the GDB server created by the Cortex "
        "Debug. Default: False."
    ),
)
@click.option(
    "--device",
    type=str,
    help=(
        "Set the target device directly, instead of getting it from the "
        "[bold]runners.yaml[/] file."
    ),
)
@click.option(
    "--gdb-path",
    type=str,
    help=(
        "Set the GDB path directly, instead of getting it in the "
        "[bold]runners.yaml[/] file."
    ),
)
@click.option(
    "--elf-file",
    type=str,
    help=("Set the elf file directly. Default [bold]build/zephyr/zephyr.elf[/]."),
)
@click.option(
    "--svd-file",
    type=str,
    help=("Set the SVD file directly, instead of trying to determine it."),
)
@click.option(
    "--no-py",
    is_flag=True,
    help=(
        "Use regular arm-zepher-eabi-gdb instead of python version for gdbPath in "
        "config. Enable this if you are facing an error while trying to use RTT "
        "in VSCode. Default: False."
    ),
)
def cortex_debug(
    east, build_dir, rtt_config, device, gdb_path, elf_file, svd_file, no_py
):
    """Create a configuration file for the [bold green]Cortex Debug[/] VScode extension.

    \b
    \n\nRunning this command inside the application project directory creates a [bold].vscode/launch.json[/] file that configures the [bold green]Cortex Debug[/] for debugging that project.

    \b
    \n\nIf the command is run without any extra options then it will try to infer the required info from the [bold]runners.yaml[/] file. If that is not desired then the --device, --gdb and --elf options can be used to provide info directly.

    \b
    \n\nSVD files for Nordic chips are determined automatically. You can override this with the --svd-file option.

    """
    east.pre_workspace_command_check()

    # If not all params are provided, try to infer them from the runners.yaml file.
    if not all([device, gdb_path, elf_file]):
        try:
            _device, _gdb_path, _elf_file = get_cortex_debug_params(build_dir)
            device = device if device else _device
            gdb_path = gdb_path if gdb_path else _gdb_path
            elf_file = elf_file if elf_file else _elf_file
        except Exception as e:
            east.print(f"Error: {e}. Can't create the .vscode/launch.json file.")
            east.exit()

    if no_py:
        gdb_path = gdb_path.replace("-py", "")

    attach = {
        "name": "Attach",
        "device": device,
        "executable": elf_file,
        "cwd": "${workspaceFolder}",
        "request": "attach",
        "type": "cortex-debug",
        "runToEntryPoint": "main",
        "servertype": "jlink",
        "gdbPath": gdb_path,
    }

    if rtt_config:
        attach["rttConfig"] = {
            "enabled": True,
            "address": "auto",
            "decoders": [{"port": 0, "type": "console"}],
        }

    if not svd_file:
        svd_file = determine_svd_file(east, device)

    if svd_file:
        attach["svdFile"] = svd_file

    # Debug JSON object is mostly the same.
    debug = copy.deepcopy(attach)
    debug["name"] = "Debug"
    debug["request"] = "launch"

    launch = {
        "version": "0.2.0",
        "configurations": [debug, attach],
    }

    vscode_dir = os.path.join(east.project_dir, ".vscode")
    os.makedirs(vscode_dir, exist_ok=True)

    launch_file = os.path.join(vscode_dir, "launch.json")
    if os.path.isfile(launch_file):
        if not rich.prompt.Confirm.ask(
            "File [bold magenta].vscode/launch.json[/] already exists. "
            "Do you want to overwrite it (y/n)?",
            show_choices=False,
            show_default=False,
        ):
            east.exit()

    with open(launch_file, "w") as f:
        json.dump(launch, f, indent=4)

    east.print(
        "Created [bold magenta].vscode/launch.json[/] file in project directory."
    )
