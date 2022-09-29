import os
import re
import sys

import click
import rich_click

from .constants import (
    CACHE_DIR,
    CONDA_PATH,
    EAST_DIR,
    MINICONDA_DIR,
    NRF_TOOLCHAIN_MANAGER_PATH,
)
from .east_context import EastContext
from .helper_functions import check_python_version, download_files


def _get_conda_download_link():
    """Construct download link for conda installer script based on system python
    version"""

    # Link to the conda installer script. Two big Xs will be later replaced with python
    # version, like 39 or 38.
    link = "https://repo.anaconda.com/miniconda/Miniconda3-pyXX_4.12.0-Linux-x86_64.sh"
    py_ver = str(sys.version_info.major) + str(sys.version_info.minor)
    return re.sub("XX", py_ver, link)


def _install_conda(east: EastContext, installer_path: str):
    """Installs Conda package manager"""

    # Conda is not on path, but the miniconda dir could still exist.
    # If we do not delete it now the installer will complain
    east.run(f"rm -fr {MINICONDA_DIR}")

    with east.console.status(
        "[bold blue]Conda processing things...", spinner_style="bold blue"
    ):
        # -b flag stands for '[b]e silent', hahaha....
        east.run(f"bash {installer_path} -b ")

        # Conda is now installed, but not on the path yet (this will happen after
        # sourcing .bashrc, .zshrc, .fishrc, etc..), so we talk to it with fullpath
        # Do not activate base env.
        east.run(f"{CONDA_PATH} config --set auto_activate_base false")
        east.run(f"{CONDA_PATH} init")


def _install_toolchain_manager(east: EastContext, exe_path: str):
    """Installs toolchain manager to a proper location"""

    # Move toolchain manager to its proper place
    east.run(f"mv -f {exe_path} {EAST_DIR}")

    # That is octal, make it executable
    os.chmod(NRF_TOOLCHAIN_MANAGER_PATH, 0o777)

    # Configure the toolchain path
    east.run(f"{NRF_TOOLCHAIN_MANAGER_PATH} config --install-dir {EAST_DIR}")


def _get_toolchain_download_link():
    """Just a convenience function for getting the link for the Nordic's toolchain
    manager executable.

    This link will be updated regularly to follow the progress on the Nordic's repo.

    Current version of the executable is v0.8.0.
    """

    link = (
        "https://github.com/NordicSemiconductor/pc-nrfconnect-toolchain-manager/"
        "blob/2f24ef572b8a7182cb6838fc2f080ad1b4fee448/resources/"
        "nrfutil-toolchain-manager/linux/nrfutil-toolchain-manager.exe?raw=true"
    )
    return link


conda_installed_msg = """
[bold green]Conda install done![/]

Close and reopen your terminal window or source your shell configuration file
manually with one of the below commands for changes to take effect:
• source ~/.bashrc
• source ~/.zshrc
• source ~/.config/fish/config.fish
"""

toolchain_installed_msg = """
[bold green]Nordic's Toolchain Manager install done![/]

East will now smartly use Nordic's Toolechain Manager whenever it can.
"""


packages = [
    {
        "exe": "conda",
        "url": _get_conda_download_link(),
        "install_method": _install_conda,
        "installed_msg": conda_installed_msg,
    },
    {
        "exe": NRF_TOOLCHAIN_MANAGER_PATH,
        "url": _get_toolchain_download_link(),
        "install_method": _install_toolchain_manager,
        "installed_msg": toolchain_installed_msg,
    },
]


@click.command(cls=rich_click.RichCommand, options_metavar="[options]")
@click.pass_obj
def sys_setup(east):
    """Perform system-wide setup for development.

    \b
    \n\nCheck if all required packages are available on the host system.

    If not, download and install them.

    \b
    \n\nPackages:\n
    - Conda Package Manager

    - Nordic's nRF Toolchain Manager executable
    """

    # TODO: Add check that this command is run outside of East/West workspace
    check_python_version(east)

    # Construct a list of files that have to be downloaded.
    east.print(
        "[blue]Checking for required system packages and programs...", highlight=False
    )
    urls = []
    for package in packages:
        package["installed"] = east.check_exe(package["exe"])
        if package["installed"]:
            east.print(f"{package['exe']} [green]found", highlight=False)
        else:
            east.print(f"{package['exe']} [red]not found", highlight=False)
            urls.append(package["url"])

    if all([package["installed"] == True for package in packages]):
        east.print("\n[green]All required system packages and programs are installed.")
        east.exit()

    # Download all required files, which are actually programs or installer scripts
    paths = download_files(urls, CACHE_DIR)

    # Run an installation method for packages that are not installed.
    for id, package in enumerate(packages):
        if not package["installed"]:
            package["install_method"](east, paths[id])

    # WARN: We assume that download_files will never fail. Depending on the urgency we
    # should implement better handling.
    # Print installed message for packages that were installed
    for package in packages:
        if not package["installed"]:
            east.console.rule("", style="")
            east.print(package["installed_msg"])
    east.console.rule("", style="")
