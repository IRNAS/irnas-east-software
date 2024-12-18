import importlib.metadata
import inspect
import json
import os
import signal
import subprocess
import sys
import time
from shutil import which

import requests
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich_click import RichCommand, RichGroup

from .constants import const_paths
from .east_yml import EastYmlLoadError, format_east_yml_load_error_msg, load_east_yml
from .helper_functions import (
    WestConfigNotFound,
    WestDirNotFound,
    WestYmlNotFound,
    get_ncs_and_project_dir,
    ncs_version_not_supported_msg,
    no_toolchain_manager_msg,
    no_toolchain_msg,
    not_in_west_workspace_msg,
    west_topdir,
)

# Needs to be exposed like this so it can be set to False in tests.
RICH_CONSOLE_ENABLE_MARKUP = True

"""
Convenience dicts for storing settings that are identical across Click's commands and
groups.
"""
east_command_settings = {
    "cls": RichCommand,
    "options_metavar": "[options]",
}

east_group_settings = {
    "cls": RichGroup,
    "options_metavar": "[options]",
}


class EastContext:
    """Context-aware API wrapper & state-passing object.

    EastContext object needs to be created in the top level cli command that groups all
    other commands. That object then needs to be passed to every other subcommand.

    Specifically, the class offers wrappers for core API calls (such as `.run`)
    which take into account CLI parser flags, configuration files, and/or
    changes made at runtime.
    """

    def __init__(self, echo: bool = False):
        """Create a new context object.

        Args:
            echo (bool): If True `.run` prints the command string to local stdout prior
            to executing it. Default: ``False``.
        """
        # This init will be called on true command invocation, --help flag or similar
        # do not count.
        self.cwd = os.getcwd()
        self.echo = echo
        self.consts = const_paths

        # Create east, tooling and cache dirs, if they do not exist.
        os.makedirs(self.consts["east_dir"], exist_ok=True)
        os.makedirs(self.consts["tooling_dir"], exist_ok=True)
        os.makedirs(self.consts["cache_dir"], exist_ok=True)

        self.console = Console(width=80, markup=RICH_CONSOLE_ENABLE_MARKUP)
        self.use_toolchain_manager = False
        self.detected_ncs_version_installed = False
        self.east_yml = None

        try:
            self.west_dir_path = west_topdir()
            self.detected_ncs_version, self.project_dir = get_ncs_and_project_dir(
                self.west_dir_path
            )

        except (WestDirNotFound, WestConfigNotFound, WestYmlNotFound):
            self.west_dir_path = None
            self.detected_ncs_version = None
            self.project_dir = None

        self.check_for_new_east_version()

    def chdir(self, path: str):
        """Change directory.

        self ():
        path (str): Relative or absolute path of the directory to change to.
        """
        os.chdir(path)
        self.cwd = os.getcwd()

    def print(self, *objects, **kwargs):
        """Prints to the console.

        Internally it uses Console object, so whatever Console can do, this function can
        also do.

        Full documentation here:
        https://rich.readthedocs.io/en/latest/reference/console.html#rich.console.Console.print
        """
        self.console.print(*objects, **kwargs)

    def print_info(self, info: str):
        """Prints a message, with many rich settings disabled, with magnify icon
        prepended. Suitable for printing info messages that should not be formatted.
        """
        self.print(
            ":mag_right: " + info,
            markup=True,
            style="bold italic dim",
            overflow="ignore",
            crop=False,
            highlight=False,
            soft_wrap=False,
            no_wrap=True,
        )

    def print_markdown(self, *objects, **kwargs):
        """Interprets given object (string) as Markdown style text and prints it to the
        console.

        Internally it uses Markdown object, so whatever Markdown can do, this function
        can also do.
        https://rich.readthedocs.io/en/stable/reference/markdown.html#rich.markdown.Markdown

        Bonus thing: Any kwargs that are passed to it are correctly sorted and either
        passed to the Markdown object or to the internal self.print function which uses
        Console object.
        """
        markdown_kwargs = {}
        print_kwargs = {}

        for key, value in kwargs.items():
            # The same key can be in both functions so we have to check against both of
            # them.
            if key in inspect.signature(Markdown).parameters.keys():
                markdown_kwargs[key] = value
            if key in inspect.signature(self.console.print).parameters.keys():
                print_kwargs[key] = value

        self.print(Markdown(*objects, **markdown_kwargs), **print_kwargs)

    def exit(self, return_code: int = 1):
        """Exit program with given return_code."""
        sys.exit(return_code)

    def run(
        self,
        command: str,
        exit_on_error: bool = True,
        return_output: bool = False,
        silent: bool = False,
        ignore_sigint: bool = False,
    ) -> dict:
        """Executes given command in shell as a process.

        This is a blocking call, process needs to finish before this command can return;

        Args:
            command (str):  Command to execute.

            exit_on_error (str):    If true the program is exited if the return code of
                                    the ran command is not 0.

            return_output (bool):   Return stdout. Note that this will mean that there
                                    might be no colorcodes in the terminal output and
                                    no strerr, due to piping.

            silent (bool):          Do not print command's output.

            ignore_sigint (bool):   If true it does not pass SIGINT to the run process.
                                    This means that the run process will handle SIGINT
                                    by itself. This is useful for running gdb.

        Returns:
            Dict with two keys is always returned:
                output(str):        Contains stdout of the process that run, if
                                    return_output is True, otherwise empty string.
                returncode(int):    Return code of the process that run
        """
        if self.echo:
            self.print_info(command)

        if return_output:
            # Prepare variable for later assignment
            returncode = None

            # This works but it has no color and no stderr
            def execute(cmd, exit_on_error):
                """Helper function that correctly executes the process and returns
                output.
                """
                popen = subprocess.Popen(
                    cmd,
                    shell=True,
                    bufsize=1,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                )
                for stdout_line in iter(popen.stdout.readline, ""):
                    yield stdout_line
                popen.stdout.close()
                rc = popen.wait()

                # Assign to global, so the value can be seen outside
                nonlocal returncode
                returncode = rc

                if exit_on_error and rc:
                    self.exit(rc)

            output = []

            for line in execute(command, exit_on_error):
                output.append(line)
                if not silent:
                    print(line, end="")

            return {"output": "".join(output), "returncode": returncode}

        else:
            out = None
            err = None

            if silent:
                out = subprocess.DEVNULL
                err = subprocess.STDOUT

            if ignore_sigint:
                previous_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
                p = subprocess.Popen(command, stdout=out, stderr=err, shell=True)
                p.wait()
                signal.signal(signal.SIGINT, previous_handler)
            else:
                p = subprocess.Popen(command, stdout=out, stderr=err, shell=True)
                p.wait()

            # Should we exit on the error?
            if exit_on_error and p.returncode:
                self.exit(p.returncode)

            return {"output": "", "returncode": p.returncode}

    def run_west(self, west_command: str, **kwargs) -> str:
        """Run wrapper which should be used when executing commands with west tool.

        If toolchain for the detected ncs version is installed then west through
        nrfutil toolchain-manager is used. If it is not installed then west is used
        directly.

        Args:
            west_command (str):     west command to execute
            kwargs:                 Anything that is supported by .run method

        Returns:
            Check .run
        """
        cmd = f"west {west_command}"

        if self.use_toolchain_manager:
            # Run west command as arbitrary command through manager
            return self.run_cmd_in_manager(cmd, **kwargs)
        else:
            return self.run(cmd, **kwargs)

    def enter_manager_shell(self):
        """Enters nrfutil toolchain-manager shell using detected NCS version."""
        cmd = (
            f"{self.consts['nrfutil_path']} toolchain-manager launch --ncs-version"
            f" {self.detected_ncs_version} --shell"
        )

        return self.run(cmd)

    def run_manager(self, command: str, **kwargs):
        """Executes a command with nrfutil toolchain-manager executable.

        This is not suitable to be used with a type of a 'launch -- <command>' command.
        For that run_cmd_in_manager should be used.

        Args:
            command (str):      Command to execute.
            kwargs:             Anything that is supported by .run method.

        Returns:
            Check .run
        """
        cmd = f"{self.consts['nrfutil_path']} toolchain-manager {command}"

        return self.run(cmd, **kwargs)

    def run_cmd_in_manager(self, command: str, **kwargs):
        """Run an arbitrary command through nrfutil toolchain-manager.

        This method should be used when passing any arbitrary command, like west command.

        Args:
            command (str):          Command to execute.
            exit_on_error (bool):   If true the program is exited if the return code of
                                    the ran command is not 0.
            **kwargs:               Anything that is supported by .run method.

        Returns:
            Check .run
        """
        cmd = (
            f"{self.consts['nrfutil_path']} toolchain-manager launch --ncs-version"
            f" {self.detected_ncs_version} -- {command}"
        )

        return self.run(cmd, **kwargs)

    def check_exe(self, exe: str, on_fail_exit: bool = False) -> bool:
        """Checks if the given executable can be found by the which command.

        If on_fail_exit is true it exits the program.

        Args:
            exe (str):              executable to find
            on_fail_exit (bool):    If true it exits cli on exit

        Returns:
            True if given executable was found, false otherwise.
        """
        if not which(exe):
            if on_fail_exit:
                self.exit()
            return False

        return True

    def check_version(self, exe, expected_version, version_cmd="--version"):
        """Checks for version of provided exe program and compares it against
        provided one.

        """
        # WARN: Check version is not yet used anywhere, behaviour yet needs to be
        # verified
        response = self.run(f"{exe} {version_cmd}", silent=True, return_output=True)

        return True if expected_version in response["output"] else False

    def pre_workspace_command_check(
        self,
        ignore_uninstalled_ncs: bool = False,
        ignore_unsupported_ncs: bool = True,
        check_only_west_workspace: bool = False,
    ):
        """This function contains a list of checks that every workspace (not system)
        command should call before executing its actual command.

        In current implementation it does general things:
        * Asserts that workspace command was run from the west workspace
        * Tries to load east.yml
        * Tries to determine the NCS version that is used in the project.
        * Tries to find the version of the toolchain in the nrfutil toolchain-manager.

        This function esentially tries to answer the question: should the underlying
        west command be passed to the nrfutil toolchain-manager or directly to the
        west.

        Args:
            ignore_uninstalled_ncs (bool):  When true, do not exit if detected
                                            NCS version is not installed by the
                                            toolchain-manager. Workspace commands such
                                            as build, flash, clean should set this to
                                            False. install toolchain command should set
                                            this to True.

            ignore_unsupported_ncs (bool):  When true, do not exit if detected
                                            NCS version is not supported by the
                                            toolchain-manager. Workspace commands such
                                            as build, flash, clean should set this to
                                            True. install toolchain command should set
                                            this to False.

            check_only_west_workspace (bool): When true, only check if we are in the
                                              west Workspace, do not check for the rest
                                              of the things. This is useful for the
                                              codechecker command, which should be run
                                              inside the west workspace, but does not
                                              need nrf toolchain manager.
        """
        # Workspace commands can only be run inside west workspace, so exit if that is
        # not the case.
        if not self.west_dir_path:
            self.print(not_in_west_workspace_msg, highlight=False)
            self.exit()

        if check_only_west_workspace:
            return

        # Exit if east.yml could not be loaded from the project dir; it is not an error
        # if it does not exist, we support that.
        try:
            self.east_yml = load_east_yml(self.project_dir)
        except EastYmlLoadError as msg:
            self.print(format_east_yml_load_error_msg(msg), highlight=False)
            self.exit()

        if os.environ.get("EAST_DONT_USE_TOOLCHAIN_MANAGER", "0") == "1":
            # Running in docker, we shouldn't use the toolchain manager.
            self.use_toolchain_manager = False
            return

        # Check if ncs version was even detected, this can happen in the cases where
        # normal zephyr repo is used.
        if self.detected_ncs_version is None:
            self.use_toolchain_manager = False
            return

        # Exit if manager is not installed.
        if not self.check_exe(self.consts["nrfutil_path"]):
            self.print(no_toolchain_manager_msg, highlight=False)
            self.exit()

        # If it is installed then we should use it.
        self.use_toolchain_manager = True

        # Early exit if toolchain for the detected ncs version is installed.
        result = self.run_manager("list", silent=True, return_output=True)
        if self.detected_ncs_version in result["output"]:
            self.detected_ncs_version_installed = True
            return

        # Check if toolchain for detected ncs version is supported
        result = self.run_manager(
            "search --show-all --json", silent=True, return_output=True
        )

        supported_ncs_versions = json.loads(result["output"])["data"]["ncs_versions"]

        if self.detected_ncs_version in supported_ncs_versions:
            # Supported but not installed, should we exit program or silently pass?
            if ignore_uninstalled_ncs:
                return

            self.print(no_toolchain_msg(self), highlight=False)
            self.exit()

        # Not supported, should we silently pass or exit program with message?
        if ignore_unsupported_ncs:
            # Silently pass
            return

        # Exit program, this is usually happens, if we want to install the toolchain.
        self.print(
            ncs_version_not_supported_msg(self, supported_ncs_versions), highlight=False
        )
        self.exit()

    def check_for_new_east_version(self):
        """Occasionally check if there is a new version of east available.

        If there is print a message to the user.
        """
        # Check if the file exists
        check_file = os.path.join(self.consts["cache_dir"], "last_version_check")
        if not os.path.isfile(check_file):
            # File does not exist, create it and write current time to it
            with open(check_file, "w") as f:
                f.write(str(time.time()))
            return

        # File exists, read the time from it
        with open(check_file, "r") as f:
            last_check = float(f.read())

        # Check if the time difference is more than 2 hours
        if (time.time() - last_check) < 2 * 3600:
            return

        # More than 2 hours, send a request
        try:
            response = requests.get("https://pypi.org/pypi/east-tool/json", timeout=1)
        except requests.exceptions.RequestException:
            # Something went wrong, do not do anything
            return

        # Check if the request was successful
        if response.status_code != 200:
            # Something went wrong, do not do anything
            return

        # Check if the version is different
        pypi_version = response.json()["info"]["version"]
        current_version = importlib.metadata.version("east-tool")
        if pypi_version != current_version:
            # Print a message that there is a new version available
            msg = (
                "\n[bold yellow]New version of east is available![/]\n"
                "Run [bold]pip install --upgrade east-tool[/] to update.\n"
            )
            self.print(Panel(msg))

        # Write current time to the file to track when the last check was performed
        with open(check_file, "w") as f:
            f.write(str(time.time()))
