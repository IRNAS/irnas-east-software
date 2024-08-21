import glob
import json
import os
import platform
import shutil

from rich.panel import Panel

from ..east_context import EastContext
from ..helper_functions import download_files


def _install_nrfutil(east: EastContext, exe_path: str):
    """Install nrfutil to a proper location."""
    nrfutil = east.consts["nrfutil_path"]
    dir = os.path.dirname(nrfutil)

    shutil.rmtree(dir, ignore_errors=True)
    os.mkdir(dir)

    east.run(f"mv -f {exe_path} {nrfutil}")

    # That is octal, make it executable.
    os.chmod(nrfutil, 0o777)

    # Pin the nrfutil to a fixed version to prevent any future breaking changes.
    # Output of --version flag on linux:
    # nrfutil 7.11.1 (7c99be8 2024-05-30)
    # commit-hash: 7c99be87b691a9ea8c7d95a2190356eddad33329
    # commit-date: 2024-05-30
    # host: x86_64-unknown-linux-gnu
    # build-timestamp: 2024-05-30T12:49:04.315203564Z
    # classification: nrf-external
    east.run(f"{nrfutil} self-upgrade --to-version 7.11.1")

    # Install toolchain-manager and configure the toolchain path.
    east.run(f"{nrfutil} install toolchain-manager")

    # Below step shouldn't be done on macOS, the install-dir is hardcoded there.
    if platform.system() != "Darwin":
        east.run(
            f"{nrfutil} toolchain-manager config --set install-dir="
            f"{east.consts['east_dir']}"
        )


def _get_nrfutil_download_link():
    """Return link for the Nordic's nRF Util executable.

    The link depends on the platform that the East is running on, however it will always
    point to a lightweight launcher version of the nrfutil.

    Check https://developer.nordicsemi.com/.pc-tools/nrfutil/ for interesting stuff.
    """
    system = platform.system()

    if system == "Linux":
        system = "x64-linux"
    elif system == "Windows":
        system = "x64-windows"
    elif system == "Darwin":
        system = "universal-osx"
    else:
        print(
            f"Unsupported system ({system}), East will download x64-linux version "
            "of nrfutil."
        )
        system = "x64-linux"

    return f"https://developer.nordicsemi.com/.pc-tools/nrfutil/{system}/nrfutil"


def _get_cppcheck_download_link():
    """Just a convenience function for getting the link for the Cppcheck source code.
    This link will be updated regularly.

    """
    link = "https://github.com/danmar/cppcheck/archive/refs/tags/2.12.0.tar.gz"
    return link


def _install_cppcheck(east: EastContext, exe_path: str):
    """Install cppcheck to a proper location."""
    # FIXME: Change how you are getting path
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
    """Return link for the clang+llvm binaries.

    This link will be updated regularly.
    """
    version = "16.0.0"

    arch = platform.machine().lower()

    if arch == "x86_64":
        arch = "x86_64-linux-gnu-ubuntu-18.04"
    elif arch == "aarch64":
        arch = "aarch64-linux-gnu"
    elif arch == "arm64":
        arch = "arm64-apple-darwin22.0"
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
    """Install clang+llvm to a proper location."""
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
    """Install codechecker to a proper location."""
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
[bold magenta]nrfutil toolchain-manager[/] install done!

East will now smartly use [bold magenta]nrfutil toolchain-manager[/] whenever it can.

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


def tool_installer(east, tool_names):
    """Install tools that are passed in the tool_names list."""
    # List of supported tools that can be installed by East.
    supported_tools = [
        {
            "name": "toolchain-manager",
            "cmd": east.consts["nrfutil_path"] + " toolchain-manager",
            "url": _get_nrfutil_download_link(),
            "install_method": _install_nrfutil,
            "installed_msg": toolchain_installed_msg,
        },
        {
            "name": "cppcheck",
            "exe": east.consts["cppcheck_path"],
            "url": _get_cppcheck_download_link(),
            "install_method": _install_cppcheck,
            "installed_msg": cppcheck_installed_msg,
        },
        {
            "name": "clang+llvm",
            "exe": east.consts["clang_path"],
            "url": _get_clang_download_link(),
            "install_method": _install_clang_llvm,
            "installed_msg": clang_llvm_installed_msg,
        },
        {
            "name": "codechecker",
            "exe": east.consts["codechecker_path"],
            "url": _get_codechecker_download_link(),
            "install_method": _install_codechecker,
            "installed_msg": codechecker_installed_msg,
        },
    ]

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
        if "exe" in tool:
            tool["installed"] = east.check_exe(tool["exe"])
            tool_path = tool["exe"]
        else:
            ret = east.run(tool["cmd"], exit_on_error=False, silent=True)
            tool["installed"] = ret["returncode"] == 0
            tool_path = tool["cmd"]

        if tool["installed"]:
            east.print(f"{tool_path} [green]found", **print_args)
        elif tool["name"] in downloaded_files:
            east.print(
                f"{tool_path} [red]not installed[/], but downloaded file is "
                f"present in the {east.consts['cache_dir']}",
                **print_args,
            )
        else:
            east.print(f"{tool_path} [red]not found", **print_args)
            files_to_download.append(
                {
                    "url": tool["url"],
                    "name": tool["name"],
                }
            )

    if all([tool["installed"] is True for tool in tools]):
        east.print("\n[green]All required tools are installed.")

    # Download all required files, which are actually programs or installer scripts.
    download_files(files_to_download, east.consts["cache_dir"])

    # Run an installation method for packages that are not installed.
    for tool in tools:
        if not tool["installed"]:
            exe_path = os.path.join(east.consts["cache_dir"], tool["name"])
            tool["install_method"](east, exe_path)

    # WARN: We assume that download_files will never fail. Depending on the urgency we
    # should implement better handling.
    for tool in tools:
        if not tool["installed"]:
            east.console.rule("", style="")
            east.print(tool["installed_msg"])
    east.console.rule("", style="")
