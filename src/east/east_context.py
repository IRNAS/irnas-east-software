import inspect
import os
import subprocess
import sys
from shutil import which

import click
from rich.console import Console
from rich.markdown import Markdown
from rich_click import RichCommand, RichGroup

from .constants import EAST_DIR, NRF_TOOLCHAIN_MANAGER_PATH
from .helper_functions import (
    WestDirNotFound,
    get_ncs_version,
    ncs_version_not_supported_msg,
    no_toolchain_manager_msg,
    no_toolchain_msg,
    not_in_west_workspace_msg,
    west_topdir,
)

"""
Conveniece dicts for storing settings that are indentical across Click's commands and
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

        # This init will be called on true command invocation, --help flag or similiar
        # do not count.
        self.cwd = os.getcwd()
        self.echo = echo
        self.console = Console(width=80)
        self.run(f"mkdir -p {EAST_DIR}")
        self.ncs_version_installed = False
        self.ncs_version_supported = False

        try:
            self.west_dir_path = west_topdir()
            self.detected_ncs_version = get_ncs_version(self.west_dir_path)

        except WestDirNotFound:
            self.west_dir_path = None
            self.detected_ncs_version = None

    def print(self, *objects, **kwargs):
        """Prints to the console.

        Internally it uses Console object, so whatever Console can do, this function can
        also do.

        Full documentation here:
        https://rich.readthedocs.io/en/latest/reference/console.html#rich.console.Console.print
        """
        self.console.print(*objects, **kwargs)

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

    def exit(self):
        """Exit program"""
        sys.exit()

    def run(
        self,
        command: str,
        exit_on_error: bool = True,
        return_output: bool = False,
        silent: bool = False,
    ) -> str:
        """
        Executes given command in shell as a process. This is a blocking call, process
        needs to finish before this command can return;

        Args:
            command (str):  Command to execute.

            exit_on_error (str):    If true the program is exited if the return code of
                                    the ran command is not 0.

            return_output (bool):   Return stdout. Note that this will mean that there
                                    might be no colorcodes in the terminal output and
                                    no strerr, due
                                    to piping.

            silent (bool):  Do not print command's output.
        """
        if self.echo:
            self.console.print(
                ":mag_right: " + command,
                markup=True,
                style="bold italic dim",
                overflow="ignore",
                crop=False,
                highlight=False,
                soft_wrap=False,
                no_wrap=True,
            )

        if return_output:
            # This works but it has no color and no stderr
            def execute(cmd, exit_on_err):
                """Helper function that correctly executes the process and returns
                output.
                """
                popen = subprocess.Popen(
                    cmd,
                    shell=True,
                    bufsize=1,
                    stdout=subprocess.PIPE,
                    universal_newlines=True,
                )
                for stdout_line in iter(popen.stdout.readline, ""):
                    yield stdout_line
                popen.stdout.close()
                return_code = popen.wait()
                if exit_on_err and return_code:
                    self.exit()

            output = []

            for line in execute(command, exit_on_error):
                output.append(line)
                if not silent:
                    print(line, end="")
            return "".join(output)

        else:
            out = None
            err = None

            if silent:
                out = subprocess.DEVNULL
                err = subprocess.STDOUT

            p = subprocess.Popen(command, stdout=out, stderr=err, shell=True)
            p.communicate()

            # Should we exit on the error?
            if exit_on_error and p.returncode != 0:
                self.exit()

    def run_west(self, west_command: str, **kwargs) -> str:
        """Run wrapper which should be used when executing commands with west tool.

        If toolchain for the detected ncs version is installed then west through
        Nordic's Toolchain manager is used. If it is not installed then west is used
        directly.

        Args:
            west_command (str):    west command to execute
            kwargs:                     Anything that is supported by .run method

        Returns:
            Check .run
        """
        if self.ncs_version_installed:
            self.run_manager(
                f"launch --ncs-version {self.detected_ncs_version} -- west"
                f" {west_command}",
                **kwargs,
            )
        else:
            self.run(f"west {west_command}", **kwargs)

    def run_manager(self, command, **kwargs) -> str:
        """Run wrapper which should be used when executing commands with Nordic's
        Toolchain manager executable.

        Args:
            manager_command (str):      Manager command to execute
            kwargs:                     Anything that is supported by .run method

        Returns:
            Check .run
        """

        return self.run(f"{NRF_TOOLCHAIN_MANAGER_PATH} " + command, **kwargs)

    def check_exe(self, exe: str, on_fail_exit: bool = False) -> bool:
        """
        Checks if the given executable can be found by the which command.

        If on_fail_exit is true it exits the program.

        Args:
            exe (str):              executable to find
            on_fail_exit (bool):    If true it exits cli on exit

        Returns:
            True if given executable was found.

        """
        exe_path = which(exe)

        if not exe_path:
            if on_fail_exit:
                self.exit()
            return False

        return True

    def check_version(self, exe, expected_version, version_cmd="--version"):
        """
        Checks for version of provided exe program and compares it against
        provided one.
        """

        response = self.run(f"{exe} {version_cmd}", silent=True, return_output=True)

        if expected_version in response.stdout:
            return True
        else:
            return False

    def pre_workspace_command_check(
        self,
        ignore_uninstalled_ncs: bool = False,
        ignore_unsupported_ncs: bool = True,
    ):
        """
        A list of checks that every workspace command should call before executing its
        actual command.


        Args:
            self.(self.ontext):             self.context for printing and exiting
            ignore_uninstalled_ncs (bool):  When true, self.does not exit if detected
                                            NCS version is not installed by the
                                            Toolchain Manager. Workspace commands such
                                            as build, flash, clean should set this to
                                            False. Update command should set this to
                                            True.

            ignore_unsupported_ncs (bool):  When true, self.does not exit if detected
                                            NCS version is not supported by the
                                            Toolchain Managaer. Workspace commands such
                                            as build, flash, clean should set this to
                                            True. Update command should set this to
                                            false.
        """
        # Exit if we are not inside west workspace
        if not self.west_dir_path:
            self.print(not_in_west_workspace_msg, highlight=False)
            self.exit()

        # Exit if manager is not installed
        if not self.check_exe(NRF_TOOLCHAIN_MANAGER_PATH):
            self.print(no_toolchain_manager_msg, highlight=False)
            self.exit()

        # # Check if toolchain for detected ncs version is installed
        if self.detected_ncs_version in self.run_manager(
            "list", silent=True, return_output=True
        ):
            # If it is installed then is also supported
            self.ncs_version_installed = True
            self.ncs_version_supported = True
            return

        # Check if toolchain for detected ncs version is supported
        supported_versions = self.run_manager("search", silent=True, return_output=True)
        if self.detected_ncs_version in supported_versions:
            # Supported but not installed, should we exit program or silently pass?
            if ignore_uninstalled_ncs:
                self.ncs_version_supported = False
                return
            else:
                self.print(no_toolchain_msg(self), highlight=False)
                self.exit()

        # Not supported, should we exit program or silently pass?
        if ignore_unsupported_ncs:
            # Silently pass
            self.ncs_version_supported = False
            return

        # Exit program
        # This is usually set if we intend to install the toolchain later
        self.print(
            ncs_version_not_supported_msg(self, supported_versions), highlight=False
        )
        self.exit()
