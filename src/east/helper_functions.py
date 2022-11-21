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

    Function expects a list of urls that point to the files.

    After all files were downloaded the function returns a list of paths to the
    downloaded files in the same order as they were given.

    Downloaded files are not renamed, they have the same name as in the url. Only
    exception to this rule are raw files from the GitHub, they end with '?raw=true', so
    that part is removed.

    Args:
        urls (List[strl]):      Url that points to a file to be downloaded.

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
