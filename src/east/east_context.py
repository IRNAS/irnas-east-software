import os
import sys
import subprocess

from shutil import which
from rich.console import Console


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
        self.cwd = os.getcwd()
        self.echo = echo
        self.console = Console(width=80)

    def print(self, *objects, **kwargs):
        """Prints to the console.

        Internally it uses Console object, so whatever Console can do, this function can
        also do.

        Full documentation here:
        https://rich.readthedocs.io/en/latest/reference/console.html#rich.console.Console.print
        """
        self.console.print(*objects, **kwargs)

    def exit(self, message: str = None):
        """Exit program with a given message if it was given.

        Args:
            message (str):  Message string that will be printed.
        """
        if message:
            self.print(message)
        sys.exit()

    def run(self, command: str) -> subprocess.CompletedProcess:
        """
        Executes given command in shell as a process. This is a blocking call, process
        needs to finish before this command can return;

        Args:
            command (str):  Command to execute.

        Returns
        """
        if self.echo:
            self.print(command)

        return subprocess.run(command, shell=True)

    def run_west(self, west_command: str):
        """Run wrapper which should be used when executing commands with west tool.

        Args:
            west_command (str):    west command to execute
        """
        self.run("west " + west_command)

    def check_exe(self, exe: str, help_string: str, on_fail_exit: bool = False) -> bool:
        """
        Checks if the given executable can be found by the which command.
        If it can not it prints given help string.

        If on_fail_exit is true it exits the program.

        Args:
            exe (str):              executable to find
            help_string (str):      string to print
            on_fail_exit (bool):    If true it exists cli on exit


        Returns:
            True if given executable was found.

        """
        exe_path = which(exe)

        if not exe_path:
            self.print(help_string)

            if on_fail_exit:
                self.exit()
            return False

        return True

    def check_version(self, exe, expected_version, version_cmd="--version"):
        """
        Checks for version of provided exe program and compares it against
        provided one.
        """

        response = self.run(f"{exe} {version_cmd}")

        if expected_version in response.stdout:
            return True
        else:
            return False
