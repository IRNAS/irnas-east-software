import os
import pathlib
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from configparser import ConfigParser
from typing import List, Optional, Tuple, Union

import requests
import yaml
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TaskID,
    TextColumn,
    TransferSpeedColumn,
)

# What west's APIs accept for paths.
#
# Here, os.PathLike objects should return str from their __fspath__
# methods, not bytes. We could try to do something like the approach
# taken in https://github.com/python/mypy/issues/5264 to annotate that
# as os.PathLike[str] if TYPE_CHECKING and plain os.PathLike
# otherwise, but it doesn't seem worth it.
PathType = Union[str, os.PathLike]

# Used to keep track of supported python versions
supported_python_versions = [
    {"major": 3, "minor": 8},
    {"major": 3, "minor": 9},
]

progress = Progress(
    TextColumn("[bold blue]{task.fields[filename]}"),
    BarColumn(),
    DownloadColumn(),
    "•",
    TransferSpeedColumn(),
)


class WestDirNotFound(RuntimeError):
    """Neither the current directory nor any parent has a west workspace."""


class WestConfigNotFound(RuntimeError):
    """.west/config file does not exist."""


class WestYmlNotFound(RuntimeError):
    """west.yml file does not exist."""


def check_python_version(east):
    """Checks if current python version is supported. If not it exists with an error
    message."""

    current_py_ver = {
        "major": sys.version_info.major,
        "minor": sys.version_info.minor,
    }

    if current_py_ver not in supported_python_versions:
        vers = supported_python_versions

        east.print(
            f"You are running Python {sys.version.split(' ')[0]} which is not"
            " supported.\n"
            "Supported versions are:",
            end="",
        )

        # Nicely print a list of supported python version in markdown
        vers_str = [f"- v{ver['major']}.{ver['minor']}.x" for ver in vers]
        east.print_markdown("\n".join(vers_str))
        east.exit()


def download_file(task_id: TaskID, url: str, path: str):
    file_size = requests.head(url, allow_redirects=True).headers.get(
        "content-length", -1
    )
    response = requests.get(url, stream=True)

    progress.update(task_id, total=int(file_size))

    with open(path, "wb") as f:
        progress.start_task(task_id)
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                progress.update(task_id, advance=len(chunk))
                f.write(chunk)


def download_files(urls: List[str], dest_dir: str) -> List[str]:
    """Download concurrently multiple files from the internet to the given directory.

    Function expects a list of URLs that point to the files.

    After all files were downloaded the function returns a list of paths to the
    downloaded files in the same order as they were given.

    Downloaded files are not renamed, they have the same name as in the URL. Only
    exception to this rule are raw files from the GitHub, they end with '?raw=true', so
    that part is removed.

    Args:
        urls (List[strl]):      URL that points to a file to be downloaded.

    Return:
        files (List[str]):      List of paths to the downloaded files.
    """

    file_paths = []

    with progress:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for url in urls:
                filename = url.split("/")[-1]
                filename = re.sub("\?raw=true$", "", filename)

                if not os.path.isdir(dest_dir):
                    os.mkdir(dest_dir)

                dest_path = os.path.join(dest_dir, filename)
                file_paths.append(dest_path)

                task_id = progress.add_task("download", filename=filename, start=False)
                pool.submit(download_file, task_id, url, dest_path)

    return file_paths


def west_topdir(start: Optional[PathType] = None) -> str:
    """
    Returns the path to the parent directory of the .west/
    directory instead, where project repositories are stored.

    Args:
        start (Optional[PathType]):     Directory from where to start searching, if not
                                        given current directory is used.

    Returns:
        Full path to parent directory of the .west/ folder.
    """
    cur_dir = pathlib.Path(start or os.getcwd())

    while True:
        if (cur_dir / ".west").is_dir():
            return os.fspath(cur_dir)

        parent_dir = cur_dir.parent
        if cur_dir == parent_dir:
            # We are at top level
            raise WestDirNotFound(
                "Could not find a west workspace in this or any parent directory"
            )
        cur_dir = parent_dir


def get_ncs_and_project_dir(west_dir_path: str) -> Tuple[str, str]:
    """
    Returns version of nrf-sdk project and absolute path to the projects directory.

    This is combined, so we avoid reading .west/config file twice.

    Args:
        west_dir_path (str):        Path to the parent of .west directory. It is up to
                                    the caller to provide a correct value.

    Returns:
        Revision string of nrf-sdk project, absolute

    Raises
        WestConfigNotFound or WestYamlNotFound
    """

    config = ConfigParser()
    config_path = os.path.join(west_dir_path, ".west", "config")

    # ".west/config file could not exist, in that case we should raise an exception"
    if not os.path.isfile(config_path):
        raise WestConfigNotFound(".west/conifg file does not exists.")

    config.read(config_path)

    # Get path to west.yaml file
    project_path = os.path.join(west_dir_path, config["manifest"]["path"])
    west_yaml = os.path.join(project_path, config["manifest"]["file"])

    if not os.path.isfile(west_yaml):
        raise WestYmlNotFound("No west.yml was found ")

    # Get ncs version
    with open(west_yaml, "r") as file:
        manifest = yaml.safe_load(file)["manifest"]

    try:
        ncs = list(
            filter(
                lambda project: project["repo-path"] == "sdk-nrf", manifest["projects"]
            )
        )
    except KeyError:
        # This can happen in the case where there is no sdk-nrf repo in the west yaml
        # file, project is probably using ordinary Zephyr.
        return None, project_path

    return (ncs[0]["revision"], project_path)


def return_dict_on_match(array_of_dicts, key, value):
    """
    Search through array of dicts and return the first one where the given key matches
    the given value.
    If none are found return None.
    """
    return next((item for item in array_of_dicts if item.get(key) == value), None)


no_toolchain_manager_msg = """
[bold cyan]Nordic's Toolchain Manager[/] is [bold red]not installed[/] on this system!

To install it run:

\t[italic bold blue]east sys-setup
"""

not_in_west_workspace_msg = """
[bold yellow]West workspace[/] was [bold red]not found![/]

This command can only be run [bold]inside[/] of a [bold yellow]West workspace[/].
"""


def no_toolchain_msg(east):
    return (
        f"Current [bold cyan]NCS[/] [bold]{east.detected_ncs_version}[/] version is "
        "supported but toolchain is [bold red]not installed![/]"
        "\n\nTo install it run:"
        "\n\n\t[italic bold blue]east update toolchain\n"
    )


def ncs_version_not_supported_msg(east, supported_versions):
    vers = "\n".join(
        [f"[bold yellow]•[/] {ver}" for ver in supported_versions.strip().split("\n")]
    )

    return (
        f"[bold]East[/] detected [bold]{east.detected_ncs_version}[/] [bold cyan]NCS[/]"
        " version which is currently [bold red]not supported[/] by the Nordic's"
        " Toolchain manager.\n\nSupported versions are: \n"
        + vers
        + "\n\nThis means that you need to manually install the [bold cyan]NCS[/]"
        " toolchain by yourself.\n"
    )


def find_all_boards(east, west_board: str) -> List[str]:
    """Find all west board names by searching the boards directory

    Search for directory that contains *_defconfig file with given west_board name,
    (this is the same process that west uses to determine the boards).

    After such directory is found, scan it and try to find what board revisions are
    present and generate a list of board names and board revisions in format expected by
    west build command.

    If no folder is found or there are no revision specific files in the folder then
    just return west_board.

        east ():            East context.
        west_board (str):   Board to search for.

    Returns:
        List of west boards to be used by west build -b <board>
    """

    def dir_find(root, west_board):
        for path, _, files in os.walk(root):
            for file in files:
                if file.endswith("_defconfig"):
                    if west_board == file[: -len("_defconfig")]:
                        return path
        return None

    board_dir = dir_find(os.path.join(east.project_dir, "boards"), west_board)

    if not board_dir:
        return [west_board]

    files = os.listdir(board_dir)

    # Find all files with west board name, no matter the version
    pattern = f"^{west_board}_[0-9]?[0-9]?_[0-9]?[0-9]?_[0-9]?[0-9]?\.conf"
    matches = [file for file in files if re.match(pattern, file)]

    # Extract hardware versions and put them into format expected by the west.
    hw_versions = [
        ".".join(m.split(".")[0].replace(west_board, "").split("_")[1:])
        for m in matches
    ]
    boards = ["@".join([west_board, hw]) for hw in sorted(hw_versions)]

    return boards if boards else [west_board]


def clean_up_extra_args(args):
    """
    Clean up extra args, by adding back double quotes to the define assignments.

    Click argument automatically strips double quotes from anything that is given
    after "--". We can not know for sure from where double quotes were removed,
    however we know that CMake in at least one case requires them.
    For example, double quotes are needed, if you are assigning a list of tokens to the
    define value, like so: -DFILES="file1.txt;file2.txt".
    Double quotes are also added if there is an assignment to a flag, like:
    --some-flag=something.
    If this line gets to Cmake without double quotes, it will not be parsed
    correctly.

        args ():    Extra args, passed after '--' as Click argument.

    Returns:
        cleaned up args, already formatted as a string.
    """

    def add_back_double_quotes(arg):
        if (arg.startswith("-D") or arg.startswith("--")) and "=" in arg:
            split = arg.split("=")
            arg = f'{split[0]}="{split[1]}"'
        return arg

    return f"{' '.join(list(map(add_back_double_quotes, args)))}"
