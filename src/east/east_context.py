import inspect
import os
import subprocess
import sys
from shutil import which

from rich.console import Console
from rich.markdown import Markdown
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
Convenience dicts for storing settings that are indentical across Click's commands and
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
        self.consts = const_paths

        # Create EAST_DIR and its parents, if they do not exists
        os.makedirs(self.consts["east_dir"], exist_ok=True)

        self.console = Console(width=80, markup=RICH_CONSOLE_ENABLE_MARKUP)
        self.ncs_version_installed = False
        self.ncs_version_supported = False
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

    def exit(self, return_code: int = 1):
        """Exit program with given return_code"""
        sys.exit(return_code)

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
                    self.exit(return_code)

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
            if exit_on_error and p.returncode:
                self.exit(p.returncode)

    def run_west(self, west_command: str, **kwargs) -> str:
        """Run wrapper which should be used when executing commands with west tool.

        If toolchain for the detected ncs version is installed then west through
        Nordic's Toolchain manager is used. If it is not installed then west is used
        directly.

        Args:
            west_command (str):     west command to execute
            kwargs:                 Anything that is supported by .run method

        Returns:
            Check .run
        """

        cmd = f"west {west_command}"

        if self.ncs_version_installed:
            # Run west command as arbitary command through manager
            return self._run_arbi_manager(cmd, **kwargs)
        else:
            return self.run(cmd, **kwargs)

    def run_manager(self, command, **kwargs) -> str:
        """Executes a command with Nordic's Toolchain manager executable.

        This is not suitable to be used with a type of a 'launch -- <command>' command.
        For that _run_arbi_manager should be used.

        Args:
            manager_command (str):      Manager command to execute
            kwargs:                     Anything that is supported by .run method

        Returns:
            Check .run
        """
        cmd = f"{self.consts['nrf_toolchain_manager_path']} {command}"

        return self.run(cmd, **kwargs)

    def _run_arbi_manager(self, arbitary_command: str, **kwargs):
        """Run an arbitary command through Nordic's Toolchain Manager

        This method should be used when passing any arbitary command, like west command.

        To properly execute an arbitary command and propagate its return code to the
        caller we have do a bit of a bash shell dancing, as Nordic's Toolchain Manager
        does not do this for some commands (if west build fails then return code is not
        propagated, but issuing non-existing command does propagate up).

        What we do is that we run as a total arbitary command following:

            bash -c '{arbitary_command} && touch success.txt'

        if arbitary_command inside it fails, then `touch success.txt` is not executed.

        So we are checking for success.txt file after every call and exit if it does not
        exist.

        We also need to be carefull what quotes are we using.

        Args:
            arbitary_command (str):
            **kwargs:
        """

        arbitary_command = arbitary_command.replace("'", '"')

        cmd = (
            f"{self.consts['nrf_toolchain_manager_path']} launch --ncs-version"
            f" {self.detected_ncs_version} -- bash -c '{arbitary_command} "
            "&& touch success.txt'"
        )

        # Clean any success.txt file from before
        try:
            os.remove("success.txt")
        except FileNotFoundError:
            pass

        result = self.run(cmd, **kwargs)

        if not os.path.isfile("success.txt"):
            self.exit()

        try:
            os.remove("success.txt")
        except FileNotFoundError:
            pass

        return result

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

        This command will also load the east.yml file if it is found.


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

        # Exit if east.yml is not present in the project dir
        try:
            self.east_yml = load_east_yml(self.project_dir)
        except EastYmlLoadError as msg:
            self.print(format_east_yml_load_error_msg(msg), highlight=False)
            self.exit()

        # Exit if manager is not installed
        if not self.check_exe(self.consts["nrf_toolchain_manager_path"]):
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
