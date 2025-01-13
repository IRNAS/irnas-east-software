import os
import shutil

import click
from rich.syntax import Syntax

from ..east_context import east_command_settings, east_group_settings
from ..helper_functions import clean_up_extra_args, find_app_build_dir
from .codechecker_helpers import (
    check_for_build_folder,
    check_for_codechecker,
    check_for_codechecker_config_yaml,
    check_for_compile_commands_json,
    check_for_url,
    cleanup_compile_commands_json,
    cleanup_plist_files,
    create_skip_file,
    get_endpoint,
    get_metadata_from_codecheckerfile,
)

# Print output of the parse and diff commands, with default rich highlighting, but
# without any other wrapping, cropping.
clean_print_args = {
    "highlight": True,
    "overflow": "ignore",
    "crop": False,
    "soft_wrap": False,
    "no_wrap": True,
}


@click.command(**east_command_settings)
@click.pass_obj
@click.option(
    "-h",
    "--html",
    is_flag=True,
    help="Generate a html report, instead of printing the results in the terminal."
    "Default: false.",
)
@click.option(
    "-p",
    "--dont-cleanup-plist",
    is_flag=True,
    help="Skip plist cleanup step. Default: false.",
)
@click.option(
    "-s",
    "--skip-file",
    type=str,
    help="Set skip file instead of generating one.",
)
@click.option(
    "-file",
    "--file",
    type=str,
    help="Analyze only the given file(s) not the whole compilation database. "
    "Absolute directory paths should start with '/', relative directory paths should "
    "start with '*' and it can contain path glob pattern. "
    "Example: '/path/to/main.c', 'lib/*.c', */test*'.",
)
@click.option(
    "-a",
    "--only-analyze",
    is_flag=True,
    help="Only perfrom analyze step and cleanup plist (if enabled). Default: false.",
)
@click.option(
    "-d",
    "--build-dir",
    default="build",
    type=str,
    help="Build directory to use for analysis. Default: 'build'.",
)
def check(east, html, dont_cleanup_plist, skip_file, file, only_analyze, build_dir):
    """Run [magenta bold]Codechecker[/] analysis for a built project.

    \b
    \n\nExpects that a CodeChecker config file (codechecker_config.yaml) exists in the
    project's root dir. That file is used to configure the analysis. See https://github.com/Ericsson/codechecker/tree/master/docs/config_file.md for more information. Run [bold magenta]east codechecker example-config[/] to see a suggested config file.

    \n\nResults of analysis are printed in the terminal by default. If --html flag is given, a html report is generated instead.

    \n\nBetween analysis and parsing of the results, the intermediary plist files are by default cleaned up to remove diagnostics that are not useful. To skip this step, use --dont-cleanup-plist flag.

    \n\nCurrently removed diagnostics are:

    \n\n- [bold magenta]Ineffective bitwise and operation[/], caused by [bold cyan]LOG_*[/] macros.
    \n\n- [bold magenta]Conditional operator with identical true and false expressions[/], caused by [bold cyan]SHELL_CMD_*[/], [bold cyan]APP_EVENT_MANAGER_*[/] macros.
    \n\n- [bold magenta]Value stored to 'variable' is never read or used[/], but is actually later used in disabled [bold cyan]__ASSERT*[/] or [bold cyan]LOG_*[/] macros.
    \n\n- [bold magenta]Comparison of integers of different signs: 'int' and 'unsigned int'[/], caused by [bold cyan]INIT_OBJ_RES*[/] macros.
    \n\n- [bold magenta]Missing field 'help' initializer[/], caused by [bold cyan]SHELL_SUBCMD*[/] macros.
    \n\n- [bold magenta]integer to pointer cast pessimizes optimization opportunities[/], caused by [bold cyan]LOG_*[/] macros.
    \n\n- [bold magenta]The code calls sizeof() on a pointer type. This can produce an unexpected result[/], caused by [bold cyan]LOG_*[/], [bold cyan]EVENT_LOG*[/], [bold cyan]APP_EVENT_MANAGER_LOG*[/] macros.

    \n\nBy default, a generated skip file is used to skip needless analysis of the Zephyr, NCS and external repositories. If that is not desired, you can provide your own skip file with the --skip-file flag, check the link for more info: https://codechecker.readthedocs.io/en/latest/analyzer/user_guide/#skip


    \n\n[bold]Note:[/] This command expects that the project's build folder contains compile_commands.json

    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check(check_only_west_workspace=True)

    cc = east.consts["codechecker_path"]
    cfg = os.path.join(east.project_dir, "codechecker_config.yaml")
    cc_output_dir = os.path.join(build_dir, "codechecker")
    compile_commands = os.path.join(
        find_app_build_dir(build_dir), "compile_commands.json"
    )

    check_for_codechecker(east)
    check_for_build_folder(east, build_dir)
    check_for_compile_commands_json(east, compile_commands)
    cleanup_compile_commands_json(compile_commands)
    check_for_codechecker_config_yaml(east, cfg)

    if not skip_file:
        skip_file = create_skip_file(east, build_dir, cc_output_dir)

    # Run analyze command
    analyze_cmd = (
        f"{cc} analyze --skip {skip_file} --output {cc_output_dir} "
        f"{compile_commands} --config {cfg} "
    )

    if file:
        analyze_cmd += f"--file '{file}'"

    east.run(analyze_cmd)

    if not dont_cleanup_plist:
        cleanup_plist_files(east, cc_output_dir)

    if only_analyze:
        return

    # Run parse command
    parse_cmd = f"{cc} parse --config {cfg} {cc_output_dir} "

    if html:
        parse_cmd += f"--output {cc_output_dir} --export html "

    result = east.run(parse_cmd, exit_on_error=False, return_output=True, silent=True)

    east.print(result["output"], **clean_print_args)


@click.option(
    "-a",
    "--apply",
    is_flag=True,
    help="Apply the available automatic fixes. "
    "This causes the modification of the source code. Default: false",
)
@click.option(
    "-d",
    "--build-dir",
    default="build",
    type=str,
    help="Analysed build directory. Default: 'build'.",
)
@click.command(**east_command_settings)
@click.pass_obj
def fixit(east, apply, build_dir):
    """Apply fixes suggested by the [magenta bold]Codechecker[/].

    \b
    \n\nSome analyzers may suggest some automatic bugfixes. Most of the times these are style issues which can be fixed easily. This command handles the listing and application of these automatic fixes.

    \n\n[bold]Note:[/] This command should be ran after the [bold cyan]east codechecker check[/] command.
    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check(check_only_west_workspace=True)

    check_for_codechecker(east)
    cc_output_dir = os.path.join(build_dir, "codechecker")

    cc = east.consts["codechecker_path"]

    fixit_cmd = f"{cc} fixit {cc_output_dir}"

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

store:
  - --trim-path-prefix=/*/project
"""


@click.option(
    "--url",
    type=str,
    default=lambda: os.getenv("EAST_CODECHECKER_SERVER_URL"),
    help="URL of the Codechecker server (port number is also required). "
    "If not explicitly given then value is read from the EAST_CODECHECKER_SERVER_URL "
    "env var.",
)
@click.option(
    "-d",
    "--build-dir",
    default="build",
    type=str,
    help="Analysed build directory that should be stored. Default: 'build'.",
)
@click.command(**east_command_settings)
@click.pass_obj
def store(east, url, build_dir):
    """Store the results of the [magenta bold]Codechecker[/] analysis to a server.

    \b
    \n\n[bold]Note:[/] This command should be ran after the [bold cyan]east codechecker check[/] command.
    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check(check_only_west_workspace=True)
    check_for_codechecker(east)
    check_for_url(east, url)

    cc = east.consts["codechecker_path"]
    cfg = os.path.join(east.project_dir, "codechecker_config.yaml")
    cc_output_dir = os.path.join(build_dir, "codechecker")

    name, tag = get_metadata_from_codecheckerfile(build_dir)
    endpoint = get_endpoint(east)

    store_cmd = (
        f"{cc} store --name '{name}' --url {url.strip('/')}/{endpoint} "
        f"--config {cfg} {cc_output_dir} --tag '{tag}'"
    )

    east.run(store_cmd)


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
    check_for_codechecker(east)

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


@click.command(
    **east_command_settings,
    context_settings=dict(ignore_unknown_options=True, allow_extra_args=True),
)
@click.pass_obj
@click.option(
    "--extra-help",
    is_flag=True,
    help="Print help of the given [bold magenta]Codechecker[/] command.",
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED, metavar="")
def bypass(east, extra_help, args):
    """Directly run any [magenta bold]CodeChecker[/] command.

    \b
    \n\nInternally runs [magenta bold]codechecker[/] command, all given arguments are passed directly to it.

    \n\nTo learn more about possible [magenta bold]codechecker[/] arguments and options use --extra-help flag.


    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check(check_only_west_workspace=True)
    check_for_codechecker(east)

    cc = east.consts["codechecker_path"]

    cmd = f"{cc} "

    if args:
        cmd += f"{clean_up_extra_args(args)} "

    if extra_help:
        cmd += "--help"

    east.run(cmd)


@click.option(
    "--new",
    is_flag=True,
    help="Show results that don't exist in the last server analysis but exist in the "
    "local one. These are new issues that have arisen since the last store to the "
    "server.",
)
@click.option(
    "--resolved",
    is_flag=True,
    help="Show results that exist in the server analysis but aren't present in the "
    "local one. These are issues that have been resolved since the last store "
    "to the server.",
)
@click.option(
    "--unresolved",
    is_flag=True,
    help="Show results that appear both in the last server analysis and in the "
    "local analysis. These are issues that were present when last stored on the "
    "server and are still present locally.",
)
@click.option(
    "--html",
    is_flag=True,
    help="Generate a html report instead of printing the results in the terminal. "
    "Default: false.",
)
@click.option(
    "--url",
    type=str,
    default=lambda: os.getenv("EAST_CODECHECKER_SERVER_URL"),
    help="URL of the Codechecker server (port number is also required). "
    "If not explicitly given then value is read from the EAST_CODECHECKER_SERVER_URL "
    "env var.",
)
@click.option(
    "-d",
    "--build-dir",
    default="build",
    type=str,
    help="Local build directory to use for analysis. Default: 'build'.",
)
@click.command(**east_command_settings)
@click.pass_obj
def servdiff(east, new, resolved, unresolved, html, url, build_dir):
    """Compare local analysis against the last server analysis.

    \b
    \n\nUse one of the --new, --resolved, --unresolved flags to specify how to compare.

    \n\n[bold]Note:[/] This command should be ran after the [bold cyan]east codechecker check[/] command.

    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check(check_only_west_workspace=True)
    check_for_codechecker(east)
    check_for_url(east, url)

    cc = east.consts["codechecker_path"]
    cc_diff_output_dir = os.path.join(build_dir, "codechecker_diff")
    cc_output_dir = os.path.join(build_dir, "codechecker")

    name, _ = get_metadata_from_codecheckerfile(build_dir)
    endpoint = get_endpoint(east)

    diff_cmd = (
        f"{cc} cmd diff --basename {name} --newname {cc_output_dir} "
        f"--url {url.strip('/')}/{endpoint} "
    )

    if [new, resolved, unresolved].count(True) != 1:
        east.print(
            "\nExactly one of the [bold cyan]--new[/], [bold cyan]--resolved[/], [bold cyan]--unresolved[/] flags must be given."
        )
        east.exit()

    if new:
        diff_cmd += "--new "

    if resolved:
        diff_cmd += "--resolved "

    if unresolved:
        diff_cmd += "--unresolved "

    if html:
        shutil.rmtree(cc_diff_output_dir, ignore_errors=True)
        diff_cmd += f"--export {cc_diff_output_dir} --output html "

    result = east.run(diff_cmd, exit_on_error=False, return_output=True, silent=True)

    east.print(result["output"], **clean_print_args)

    # Propagate return code, so that if diff_cmd fails external scripts can react to
    # that.
    east.exit(result["returncode"])


@click.group(**east_group_settings, subcommand_metavar="Subcommands")
@click.pass_obj
def codechecker(east):
    """Command with several subcommands related to [magenta bold]CodeChecker[/].

    \b
    \n\nIf running CodeChecker inside continuous integration environment, run [bold cyan]export EAST_CODECHECKER_CI_MODE=1[/] before running any [bold cyan]east codechecker[/] commands.
    This will make [bold cyan]east[/] use the [magenta bold]CodeChecker[/] executable that is on the system path instead of the one in the tooling directory. The system provided [magenta bold]CodeChecker[/] will normally also want to use the system provided clang, clang-tidy and cppcheck.

    \b
    \n\nThis way users can leverage the programs provided by continuous integration
    environment and not by [bold cyan]east[/], which is usually faster due to caching.
    """
    pass


codechecker.add_command(check)
codechecker.add_command(example_config)
codechecker.add_command(fixit)
codechecker.add_command(store)
codechecker.add_command(bypass)
codechecker.add_command(servdiff)
