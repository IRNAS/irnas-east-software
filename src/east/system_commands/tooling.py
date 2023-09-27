import glob
import json
import os
import platform
import shutil

from rich.panel import Panel

from ..constants import (
    CLANG_PATH,
    CODECHECKER_PATH,
    CPPCHECK_PATH,
    NRF_TOOLCHAIN_MANAGER_PATH,
)
from ..east_context import EastContext
from ..helper_functions import download_files


def _install_toolchain_manager(east: EastContext, exe_path: str):
    """Installs toolchain manager to a proper location"""

    nrfutil_dir = os.path.join(east.consts["tooling_dir"], "nrfutil")

    shutil.rmtree(nrfutil_dir, ignore_errors=True)
    os.mkdir(nrfutil_dir)

    # Move toolchain manager to its proper place
    east.run(f"mv -f {exe_path} {east.consts['nrf_toolchain_manager_path']}")

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

    arch = platform.machine().lower()

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


def _get_codechecker_download_link():
    """Just a convenience function for getting the link for the CodeChecker source code.

    This link will be updated regularly.
    """

    version = "v6.22.2"

    link = f"https://github.com/Ericsson/codechecker/archive/refs/tags/{version}.tar.gz"

    return link


def _install_codechecker(east: EastContext, exe_path: str):
    """Installs codechecker to a proper location"""

    codechecker_dir = os.path.join(east.consts["tooling_dir"], "codechecker")

    # Remove old cppcheck dir if it exists
    shutil.rmtree(codechecker_dir, ignore_errors=True)

    shutil.unpack_archive(exe_path, east.consts["tooling_dir"], format="gztar")

    # Remove version from the folder name
    dir = glob.glob(os.path.join(east.consts["tooling_dir"], "codechecker-*"))[0]
    shutil.move(dir, codechecker_dir)

    # Set extra options package so you don't need gcc-multilib and ui code.
    east.print(
        "[bold blue]Compiling codechecker from source, this will take some time..."
    )
    result = east.run(
        f"cd {codechecker_dir} && "
        "BUILD_LOGGER_64_BIT_ONLY=YES BUILD_UI_DIST=NO make package",
        exit_on_error=False,
        return_output=True,
        silent=True,
    )

    if result["returncode"] != 0:
        east.print(
            result["output"],
            markup=False,
            style="",
            overflow="ignore",
            crop=False,
            highlight=False,
            soft_wrap=False,
            no_wrap=True,
        )

        msg = (
            "Compiling codechecker [bold red]failed[/]! Check build output above"
            "to see what went wrong.\n"
            "You probably need to install some extra packages:\n\n"
            "\t[bold italic cyan]sudo apt install build-essential curl libncurses5[/]"
        )
        east.print(Panel(msg, padding=1, border_style="red"))
        east.exit()

    east.print("[bold green]Done!")

    # Set paths to the analyzers in the config file
    # Codechecker somehow needs to know which analyzers it should use, this is the only
    # way this can be set.
    config_file = os.path.join(
        codechecker_dir, "build", "CodeChecker", "config", "package_layout.json"
    )

    with open(config_file, "r") as f:
        data = json.load(f)

    data["runtime"]["analyzers"]["clangsa"] = east.consts["clang_path"]
    data["runtime"]["analyzers"]["cppcheck"] = east.consts["cppcheck_path"]
    data["runtime"]["analyzers"]["clang-tidy"] = east.consts["clang_tidy_path"]
    data["runtime"]["clang-apply-replacements"] = east.consts["clang_replace_path"]

    with open(config_file, "w") as f:
        f.write(json.dumps(data, indent=2))


toolchain_installed_msg = """
[bold green]Nordic's Toolchain Manager install done![/]

East will now smartly use Nordic's Toolchain Manager whenever it can.

[bold]Note:[/] You still need to run [italic bold blue]east install toolchain[/] inside
of a [yellow bold]West workspace[/] to get the actual toolchain.
"""

cppcheck_installed_msg = """
[bold green]cppcheck install done![/]
"""

clang_llvm_installed_msg = """
[bold green]clang-tidy and clang analyzer install done![/]
"""

codechecker_installed_msg = """
[bold green]codechecker install done![/]
"""

supported_tools = [
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
    {
        "name": "codechecker",
        "exe": CODECHECKER_PATH,
        "url": _get_codechecker_download_link(),
        "install_method": _install_codechecker,
        "installed_msg": codechecker_installed_msg,
    },
]


def tool_installer(east, tool_names):
    tools = [tool for tool in supported_tools if tool["name"] in tool_names]

    # Construct a list of files that have to be downloaded.
    east.print("[blue]Checking for required tools...", highlight=False)

    files_to_download = []
    downloaded_files = os.listdir(east.consts["cache_dir"])

    print_args = {
        "highlight": False,
        "overflow": "ignore",
        "crop": False,
        "soft_wrap": False,
        "no_wrap": True,
    }

    for tool in tools:
        tool["installed"] = east.check_exe(tool["exe"])
        if tool["installed"]:
            east.print(f"{tool['exe']} [green]found", **print_args)
        elif tool["name"] in downloaded_files:
            east.print(
                f"{tool['exe']} [red]not installed[/], but downloaded file is "
                f"present in the {east.consts['cache_dir']}",
                **print_args,
            )
        else:
            east.print(f"{tool['exe']} [red]not found", **print_args)
            files_to_download.append(
                {
                    "url": tool["url"],
                    "name": tool["name"],
                }
            )

    if all([tool["installed"] is True for tool in tools]):
        east.print("\n[green]All required tools are installed.")

    # Download all required files, which are actually programs or installer scripts
    download_files(files_to_download, east.consts["cache_dir"])

    # Run an installation method for packages that are not installed.
    for tool in tools:
        if not tool["installed"]:
            exe_path = os.path.join(east.consts["cache_dir"], tool["name"])
            tool["install_method"](east, exe_path)

    # WARN: We assume that download_files will never fail. Depending on the urgency we
    # should implement better handling.
    # Print installed message for packages that were installed
    for tool in tools:
        if not tool["installed"]:
            east.console.rule("", style="")
            east.print(tool["installed_msg"])
    east.console.rule("", style="")
