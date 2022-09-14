from rich.console import Console
import os
import subprocess


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
        self.console = Console()

    def print(self, *objects, **kwargs):
        """Prints to the console.

        Internally it uses Console object, so whatever Console can do, this function can
        also do.

        Full documentation here:
        https://rich.readthedocs.io/en/latest/reference/console.html#rich.console.Console.print
        """
        self.console.print(*objects, **kwargs)

    def run(self, command: str):
        """
        Executes given command in shell as a process. This is a blocking call, process
        needs to finish before this command can return;

        Args:
            command (str):  Command to execute.
        """
        if self.echo:
            click.echo(command)

        subprocess.run(command, shell=True)

    def run_west(self, west_command: str):
        """Run wrapper which should be used when executing commands with west tool.

        Args:
            west_command (str):    west command to execute
        """
        self.run("west " + west_command)
