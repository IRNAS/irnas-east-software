import inspect
import os
import subprocess
import sys
from shutil import which

from rich.console import Console
from rich.markdown import Markdown

from .constants import EAST_DIR


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

        # This init will be called on true command invokation, --help flag or similiar
        # do not count.
        self.cwd = os.getcwd()
        self.echo = echo
        self.console = Console(width=80)
        self.run(f"mkdir -p {EAST_DIR}")

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

    def exit(self, message: str = None):
        """Exit program with a given message if it was given.

        Args:
            message (str):  Message string that will be printed.
        """
        if message:
            self.print(message)
        sys.exit()

    def run(self, command: str, exit_on_error: bool = False):
        """
        Executes given command in shell as a process. This is a blocking call, process
        needs to finish before this command can return;

        Args:
            command (str):  Command to execute.

            exit_on_error (str):    If true the program is exited if the return code of
                                    the ran command is not 0.
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

        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        # Print stdout and stderr as cleanly as possible through Rich Console. The
        # benefit is that we can now use spinner animations and they are not interrupted
        # by output messages from subprocess.
        for line in iter(lambda: proc.stdout.readline(), b""):
            print(line.decode("utf-8"), end="")

        # Exit on a command that failed
        if exit_on_error and proc.returncode != 0:
            self.exit()

    def run_west(self, west_command: str):
        """Run wrapper which should be used when executing commands with west tool.

        Args:
            west_command (str):    west command to execute
        """
        self.run("west " + west_command)

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

        response = self.run(f"{exe} {version_cmd}")

        if expected_version in response.stdout:
            return True
        else:
            return False
