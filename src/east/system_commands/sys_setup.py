import glob
import os
import platform
import re
import shutil
import sys

import click

from ..constants import CLANG_PATH, CPPCHECK_PATH, NRF_TOOLCHAIN_MANAGER_PATH
from ..east_context import EastContext, east_command_settings
from ..helper_functions import (
    check_python_version,
    download_files,
    return_dict_on_match,
)


def _get_conda_download_link():
    """Construct download link for Conda installer script based on system python
    version"""

    # Link to the Conda installer script. Two big Xs will be later replaced with python
    # version, like 39 or 38.
    link = "https://repo.anaconda.com/miniconda/Miniconda3-pyXX_4.12.0-Linux-x86_64.sh"
    py_ver = str(sys.version_info.major) + str(sys.version_info.minor)
    return re.sub("XX", py_ver, link)


def _install_conda(east: EastContext, installer_path: str):
    """Installs Conda package manager"""

    # Conda is not on path, but the miniconda dir could still exist.
    # If we do not delete it now the installer will complain.
    east.run(f"rm -fr {east.consts['miniconda_dir']}")

    east.print("[bold blue]Started Conda installer...")
    # -b flag stands for '[b]e silent', hahaha....
    east.run(f"bash {installer_path} -b ")

    # Conda is now installed, but not on the path yet (this will happen after
    # sourcing .bashrc, .zshrc, .fishrc, etc..), so we talk to it with fullpath
    # Do not activate base env.
    east.run(f"{east.consts['conda_path']} config --set auto_activate_base false")
    east.run(f"{east.consts['conda_path']} init")


def _install_toolchain_manager(east: EastContext, exe_path: str):
    """Installs toolchain manager to a proper location"""

    # Move toolchain manager to its proper place
    east.run(f"mv -f {exe_path} {east.consts['east_dir']}")

    # That is octal, make it executable
    os.chmod(east.consts["nrf_toolchain_manager_path"], 0o777)

    # Configure the toolchain path
    east.run(
        f"{east.consts['nrf_toolchain_manager_path']} config --install-dir "
        f"{east.consts['east_dir']}"
    )


def _get_toolchain_download_link():
    """Just a convenience function for getting the link for the Nordic's toolchain
    manager executable.

    This link will be updated regularly to follow the progress on the Nordic's repo.

    Output of --version flag:

    nrfutil-toolchain-manager 0.13.0-alpha.3 (a7ee07d 2023-05-26)
    commit-hash: a7ee07d0cbc1539dbf5f89446f558580f0cf000d
    commit-date: 2023-05-26
    host: x86_64-unknown-linux-gnu
    build-timestamp: 2023-05-26T13:54:13.429101305Z
    classification: nrf-internal
    """

    link = (
        "https://github.com/NordicSemiconductor/pc-nrfconnect-toolchain-manager/"
        "blob/7dda8ba815a0c9df52a22c943a25cb43cd622bcb/resources/"
        "nrfutil-toolchain-manager/linux/nrfutil-toolchain-manager.exe?raw=true"
    )
    return link


def _get_cppcheck_download_link():
    """Just a convenience function for getting the link for the Cppcheck source code.
    This link will be updated regularly.

    """

    link = "https://github.com/danmar/cppcheck/archive/refs/tags/2.12.0.tar.gz"
    return link


def _install_cppcheck(east: EastContext, exe_path: str):
    """Installs cppcheck to a proper location"""

    cppcheck_dir = os.path.join(east.consts["tooling_dir"], "cppcheck")

    # Remove old cppcheck dir if it exists
    shutil.rmtree(cppcheck_dir, ignore_errors=True)

    shutil.unpack_archive(exe_path, east.consts["tooling_dir"], format="gztar")

    # Remove version from the folder name
    dir = glob.glob(os.path.join(east.consts["tooling_dir"], "cppcheck-*"))[0]
    shutil.move(dir, cppcheck_dir)

    # Compile the cppcheck, no need to make it executable afterwards
    east.run(
        (
            f"cd {cppcheck_dir} && "
            f"make MATCHCOMPILER=yes FILESDIR={cppcheck_dir}/filesdir "
            'CXXFLAGS="-O2 -DNDEBUG -Wall -Wno-sign-compare -Wno-unused-function" -j8'
        )
    )


def _get_clang_download_link():
    """Just a convenience function for getting the link for the clang+llvm binaries.

    This link will be updated regularly.
    """

    version = "16.0.0"

    arch = platform.processor().lower()

    if arch == "x86_64":
        arch = "x86_64-linux-gnu-ubuntu-18.04"
    elif arch == "aarch64":
        arch = "aarch64-linux-gnu"
    elif arch == "arm64":
        arch = "arm64-apple-darwin"
    else:
        print(
            f"Unsupported architecture ({arch}), East will download x86_64 version "
            "of clang+llvm binaries."
        )
        arch = "x86_64-linux-gnu-ubuntu-18.04"

    link = (
        "https://github.com/llvm/llvm-project/releases/download/"
        f"llvmorg-{version}/clang+llvm-{version}-{arch}.tar.xz"
    )

    return link


def _install_clang_llvm(east: EastContext, exe_path: str):
    """Installs clang+llvm to a proper location"""

    clang_dir = os.path.join(east.consts["tooling_dir"], "clang+llvm")

    # Remove old clang dir if it exists
    shutil.rmtree(clang_dir, ignore_errors=True)

    east.print("[bold blue]Extracing clang+llvm binaries, this will take some time...")
    shutil.unpack_archive(exe_path, east.consts["tooling_dir"], format="gztar")
    east.print("[bold green]Done!")

    # Remove version from the folder name
    dir = glob.glob(os.path.join(east.consts["tooling_dir"], "clang+llvm-*"))[0]
    shutil.move(dir, clang_dir)


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

East will now smartly use Nordic's Toolchain Manager whenever it can.

[bold]Note:[/] You still need to run [italic bold blue]east update toolchain[/] inside
of a [yellow bold]West workspace[/] to get the actual toolchain.
"""

cppcheck_installed_msg = """
[bold green]cppcheck install done![/]
"""

clang_llvm_installed_msg = """
[bold green]clang-tidy and clang analyzer install done![/]
"""

packages = [
    # Do not install Conda for now, it is not needed.
    # {
    #     "name": "Conda",
    #     "exe": "conda",
    #     "url": _get_conda_download_link(),
    #     "install_method": _install_conda,
    #     "installed_msg": conda_installed_msg,
    # },
    {
        "name": "nrfutil-toolchain-manager.exe",
        "exe": NRF_TOOLCHAIN_MANAGER_PATH,
        "url": _get_toolchain_download_link(),
        "install_method": _install_toolchain_manager,
        "installed_msg": toolchain_installed_msg,
    },
    {
        "name": "cppcheck",
        "exe": CPPCHECK_PATH,
        "url": _get_cppcheck_download_link(),
        "install_method": _install_cppcheck,
        "installed_msg": cppcheck_installed_msg,
    },
    {
        "name": "clang+llvm",
        "exe": CLANG_PATH,
        "url": _get_clang_download_link(),
        "install_method": _install_clang_llvm,
        "installed_msg": clang_llvm_installed_msg,
    },
]


@click.command(**east_command_settings)
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

    check_python_version(east)

    # Construct a list of files that have to be downloaded.
    east.print(
        "[blue]Checking for required system packages and programs...", highlight=False
    )

    files_to_download = []
    downloaded_files = os.listdir(east.consts["cache_dir"])

    print_args = {
        "highlight": False,
        "overflow": "ignore",
        "crop": False,
        "soft_wrap": False,
        "no_wrap": True,
    }

    for package in packages:
        package["installed"] = east.check_exe(package["exe"])
        if package["installed"]:
            east.print(f"{package['exe']} [green]found", **print_args)
        elif package["name"] in downloaded_files:
            east.print(
                f"{package['exe']} [red]not installed[/], but download file is "
                f"present in the {east.consts['cache_dir']}",
                **print_args,
            )
        else:
            east.print(f"{package['exe']} [red]not found", **print_args)
            files_to_download.append(
                {
                    "url": package["url"],
                    "name": package["name"],
                }
            )

    if all([package["installed"] is True for package in packages]):
        east.print("\n[green]All required system packages and programs are installed.")
        east.exit(0)

    # Download all required files, which are actually programs or installer scripts
    download_files(files_to_download, east.consts["cache_dir"])

    # Run an installation method for packages that are not installed.
    for package in packages:
        if not package["installed"]:
            exe_path = os.path.join(east.consts["cache_dir"], package["name"])
            package["install_method"](east, exe_path)

    # WARN: We assume that download_files will never fail. Depending on the urgency we
    # should implement better handling.
    # Print installed message for packages that were installed
    for package in packages:
        if not package["installed"]:
            east.console.rule("", style="")
            east.print(package["installed_msg"])
    east.console.rule("", style="")


@click.command(**east_command_settings)
@click.pass_obj
def init(east):
    """Creates a West workspace."""
