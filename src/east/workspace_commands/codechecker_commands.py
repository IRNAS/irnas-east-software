import os

import click
from rich.syntax import Syntax

from ..east_context import east_command_settings, east_group_settings
from .codechecker_helpers import (
    check_for_build_folder,
    check_for_codechecker_config_yaml,
    check_for_compile_commands_json,
    cleanup_plist_files,
    create_skip_file,
)

CC_OUTPUT_DIR = os.path.join("build", "codechecker")


@click.command(**east_command_settings)
@click.pass_obj
@click.option(
    "-h",
    "--html",
    is_flag=True,
    help="Instead of printing the results in the terminal, generate a html report. "
    "Default: false.",
)
@click.option(
    "-p",
    "--dont-cleanup-plist",
    is_flag=True,
    help="Skips plist cleanup step. Default: false.",
)
@click.option(
    "-s",
    "--skip-file",
    type=str,
    help="Instead of generating a skip file, provide your own.",
)
@click.option(
    "-a",
    "--only-analyze",
    is_flag=True,
    help="Only perfrom analyze step and cleanup plist (if enabled). Default: false.",
)
def check(east, html, dont_cleanup_plist, skip_file, only_analyze):
    """Run [magenta bold]Codechecker[/] analysis for a project in current working directory.

    \b
    \n\nExpects that a CodeChecker config file (codechecker_config.yaml) exists in the
    project's root dir. That file is used to configure the analysis.
    See https://github.com/Ericsson/codechecker/tree/master/docs/config_file.md for more
    information. Run east codechecker example-config to see a suggested config file.

    \n\nResults of analysis are printed in the terminal by default. If --html flag is given, a html report is generated instead.

    \n\nBetween analysis and parsing of the results, the intermediary plist files are by default cleaned up to remove diagnostics that are not useful. To skip this step, use --dont-cleanup-plist flag.

    \n\nCurrently removed diagnostics are:

    \n\n- [bold magenta]Ineffective bitwise and operation[/], caused by Zephyr's [bold cyan]LOG_*[/] macros.
    \n\n- [bold magenta]Conditional operator with identical true and false expressions[/], caused by Zephyr's [bold cyan]LOG_*[/], [bold cyan]SHELL_CMD_*[/], [bold cyan]APP_EVENT_MANAGER_*[/] macros.
    \n\n- [bold magenta]Value stored to 'variable' is never read or used[/], but is actually later used in disabled [bold cyan]__ASSERT*[/] or [bold cyan]LOG_*[/] macros.

    \n\nBy default, a generated skip file is used to skip needless analysis of the Zephyr, NCS and external repositories. If that is not desired, you can provide your own skip file with the --skip-file flag, check the link for more info: https://codechecker.readthedocs.io/en/latest/analyzer/user_guide/#skip


    \n\n[bold]Note:[/] This command expects that the project's build folder contains compile_commands.json

    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check(check_only_west_workspace=True)

    cc = east.consts["codechecker_path"]
    cfg = os.path.join(east.project_dir, "codechecker_config.yaml")
    compile_commands = os.path.join("build", "compile_commands.json")

    check_for_build_folder(east)
    check_for_compile_commands_json(east, compile_commands)
    check_for_codechecker_config_yaml(east, cfg)

    if not skip_file:
        skip_file = create_skip_file(east, CC_OUTPUT_DIR)

    # Run analyze command
    analyze_cmd = (
        f"{cc} analyze --skip {skip_file} --output {CC_OUTPUT_DIR} "
        f"{compile_commands} --config {cfg}"
    )

    east.run(analyze_cmd)

    if not dont_cleanup_plist:
        cleanup_plist_files(east, CC_OUTPUT_DIR)

    if only_analyze:
        return

    # Run parse command
    parse_cmd = f"{cc} parse --config {cfg} {CC_OUTPUT_DIR } {html} "

    if html:
        parse_cmd += f"--output {CC_OUTPUT_DIR } --export html "

    result = east.run(parse_cmd, exit_on_error=False, return_output=True, silent=True)

    # Print output of the parse command, with default rich highlighting, but without any
    # other wrapping, cropping.
    print_args = {
        "highlight": True,
        "overflow": "ignore",
        "crop": False,
        "soft_wrap": False,
        "no_wrap": True,
    }
    east.print(result["output"], **print_args)


@click.option(
    "-a",
    "--apply",
    is_flag=True,
    help="Apply the available automatic fixes. "
    "This causes the modification of the source code. Default: false",
)
@click.command(**east_command_settings)
@click.pass_obj
def fixit(east, apply):
    """Apply fixes suggested by the [magenta bold]Codechecker[/].

    \b
    \n\nSome analyzers may suggest some automatic bugfixes. Most of the times these are style issues which can be fixed easily. This command handles the listing and application of these automatic fixes.

    \n\n[bold]Note:[/] This command should be ran after the [bold cyan]east codechecker check[/] command.

    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """

    east.pre_workspace_command_check(check_only_west_workspace=True)

    cc = east.consts["codechecker_path"]

    fixit_cmd = f"{cc} fixit {CC_OUTPUT_DIR}"

    if apply:
        fixit_cmd += " --apply"

    east.run(fixit_cmd)


example_config_text = """
analyzer:
  - --keep-gcc-include-fixed
  - --keep-gcc-intrin
  # Uncomment below option when you want to use .clang-tidy file.
  # - --analyzer-config=clang-tidy:take-config-from-directory=true
  - --analyzers
  - clang-tidy
  - clangsa
  - --enable=guideline:sei-cert
  # Enable for cross translation unit analyis, but analysis will take longer.
  # - --ctu

parse:
  - --trim-path-prefix=/*/project
  - --print-steps
"""


@click.option(
    "-c",
    "--create",
    is_flag=True,
    help="Create example [bold magenta]codechecker_config.yaml[/] in the project's root dir.",
)
@click.command(**east_command_settings)
@click.pass_obj
def example_config(east, create):
    """Show example [bold magenta]codechecker_config.yaml[/] file."""

    east.pre_workspace_command_check(check_only_west_workspace=True)

    if create:
        with open(os.path.join(east.project_dir, "codechecker_config.yaml"), "w") as f:
            f.write(example_config_text)

        east.print(
            "\nCreated [bold magenta]codechecker_config.yaml[/] file "
            "in project's root dir."
        )
        return

    east.print(
        "\nExample [bold magenta]codechecker_config.yaml[/] file,"
        " place this in your project's root dir:"
    )
    syntax = Syntax(
        example_config_text, "yaml", theme="ansi_dark", background_color="default"
    )
    east.print(syntax)


@click.group(**east_group_settings, subcommand_metavar="Subcommands")
@click.pass_obj
def codechecker(east):
    """Command with several subcommands related to the [magenta bold]CodeChecker[/]."""
    pass


codechecker.add_command(check)
codechecker.add_command(example_config)
codechecker.add_command(fixit)
# codechecker.add_command(store)
