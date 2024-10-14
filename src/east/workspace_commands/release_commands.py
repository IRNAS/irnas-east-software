import copy
import os
import re
import shutil as sh

import click
from rich.box import ROUNDED
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich.table import Table

from ..east_context import east_command_settings
from ..helper_functions import (
    clean_up_extra_args,
    does_project_use_sysbuild,
    find_all_boards,
    find_app_build_dir,
    get_git_version,
)
from .build_type_flag import construct_extra_cmake_arguments

# This could be considered as a hack, but it is actually the cleanest way to test
# release command.
RUNNING_TESTS = False


clean_print_args = {
    "markup": False,
    "style": "",
    "overflow": "ignore",
    "crop": False,
    "highlight": False,
    "soft_wrap": False,
    "no_wrap": True,
}


def create_artefact_name(project, board, version, build_type):
    """Create an artefact name.

    Board might be in form <west_board>@<hv_version>, in that case we modify it to fit
    the artefact name.

    We also add git hash at the end if the build was not done on the clean tagged
    commit.
    """
    # As we allow project names to be paths for samples, we need to extract just the
    # name of the project.
    project = os.path.basename(project)

    board = board.replace("@", "-hv")

    # "Normalize" hw v2 board names
    board = board.replace("/", "_")

    # "release" or None build_type should not generate any build type qualifier.
    build_type = "" if build_type == "release" or not build_type else f"-{build_type}"

    git_hash = f"-{version['hash']}" if version["hash"] else ""

    return f"{project}-{board}-{version['tag']}{build_type}{git_hash}"


def create_art_dest_and_src_dir(
    name: str,
    parent: str,
    release_dir: str,
    board: str,
    build_type: str,
    is_single_app: bool,
):
    """Create destination and source directories for the artefact."""
    common_dest = os.path.join(release_dir, parent, name)

    # "Normalize" hw v2 board names
    board = board.replace("/", "_")

    if parent == "apps":
        if build_type:
            dst = os.path.join(common_dest, build_type, board)
        else:
            dst = os.path.join(common_dest, board)
        if is_single_app:
            src_dir = "app"
        else:
            src_dir = os.path.join("app", name)
    else:
        # parent is "samples"
        dst = os.path.join(common_dest, board)
        src_dir = os.path.join("samples", name)

    return dst, src_dir


def collect_binaries_using_sysbuild(build_dir, dry_run):
    """Collect binaries from build folder that used sysbuild."""
    app_build_dir = os.path.join(find_app_build_dir(build_dir), "zephyr")

    # This two always exist.
    merged_hex = os.path.join(build_dir, "merged.hex")
    zephyr_elf = os.path.join(app_build_dir, "zephyr.elf")
    binaries = [merged_hex, zephyr_elf]

    # This one might exist.
    dfu_zip = os.path.join(build_dir, "dfu_application.zip")
    if os.path.isfile(dfu_zip):
        binaries.append(dfu_zip)

    # This one also might exist, if not use zephyr.bin instead.
    app_update_bin = os.path.join(app_build_dir, "zephyr.signed.bin")
    if not os.path.isfile(app_update_bin):
        app_update_bin = os.path.join(app_build_dir, "zephyr.bin")
    binaries.append(app_update_bin)

    if dry_run or RUNNING_TESTS:
        binaries = [merged_hex, zephyr_elf, dfu_zip, app_update_bin]

    return binaries


def collect_binaries_without_using_sysbuild(build_dir, dry_run):
    """Collect binaries from build folder that did not use sysbuild."""
    app_build_dir = os.path.join(build_dir, "zephyr")

    # Determine, if we have basic build with MCUBoot, some other build with child
    # images, or default build
    if (
        os.path.isfile(os.path.join(app_build_dir, "app_update.bin"))
        or dry_run
        or RUNNING_TESTS
    ):
        # MCUBoot
        binaries = [
            "dfu_application.zip",
            "app_update.bin",
            "merged.hex",
            "zephyr.elf",
        ]
    elif os.path.isfile(os.path.join(app_build_dir, "merged.hex")):
        # Other (TFM, SPM, ...)
        binaries = ["merged.hex", "zephyr.elf"]
    else:
        # Basic build (No merged.hex is generated)
        binaries = ["zephyr.bin", "zephyr.hex", "zephyr.elf"]

    return [os.path.join(app_build_dir, binary) for binary in binaries]


def move_build_artefacts(art_name, art_dest, job_type, spdx_app_only, dry_run):
    """Moves build artefacts to art_dest and renames them to art_name."""
    os.makedirs(art_dest, exist_ok=True)

    build_dir = "build"
    # Figure out out if sysbuild is used or not, presence of domains.yaml can be used
    # for that. Determine the default build directory.
    # Collect dfu_application.zip, zephyr.signed.bin, merged.hex, zephyr.elf, first two
    # might be missing.

    if does_project_use_sysbuild(build_dir):
        binaries = collect_binaries_using_sysbuild(build_dir, dry_run)
    else:
        binaries = collect_binaries_without_using_sysbuild(build_dir, dry_run)

    for binary in binaries:
        # If doing dry run or running tests we just create empty files so that we have
        # something to copy.
        if dry_run or RUNNING_TESTS:
            path = os.path.dirname(binary)
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            open(binary, "w").close()

        if os.path.isfile(binary):
            exten = binary.split(".")[-1]
            sh.copyfile(
                binary,
                os.path.join(art_dest, ".".join([art_name, exten])),
            )

    if spdx_app_only and job_type == "apps":
        spdx_src = os.path.join("build", "spdx")
        spdx_dest = os.path.join(art_dest, "sbom-spdx")
        sh.move(spdx_src, spdx_dest)


def show_job_summary(east, jobs):
    """Prints a summary of jobs to be run."""
    table = Table(
        show_header=True,
        header_style="bold magenta",
        title="Jobs to run",
        box=ROUNDED,
    )
    table.add_column("Name", style="dim italic", min_width=8)
    table.add_column("Type", min_width=8)
    table.add_column("West board", style="dim italic")
    table.add_column("Build type")

    for job in jobs:
        table.add_row(
            job["src_dir"].split("/")[-1],
            "app" if job["subdir"] == "apps" else "sample",
            job["board"],
            job["build_type"] if job["subdir"] == "apps" else "/",
        )

    east.print()
    east.print(table)
    east.print()


def create_build_command(
    east,
    board=None,
    build_type=None,
    build_dir=None,
    target=None,
    source_dir=None,
    cmake_args=None,
    silence_diagnostic=False,
):
    """Helper for creating a build command.

    Returns:
        build_cmd: a string with the build command, intended to be given to run_west()
    """
    build_type_args, diagnostic = construct_extra_cmake_arguments(
        east,
        build_type,
        board,
        build_dir,
        source_dir,
    )

    if diagnostic and not silence_diagnostic:
        east.print(diagnostic)

    build_cmd = "build"

    if board:
        build_cmd += f" -b {board}"
    if build_dir:
        build_cmd += f" -d {build_dir}"
    if target:
        build_cmd += f" -t {target}"
    if source_dir:
        build_cmd += f" {source_dir}"

    # Some flags need to be passed as extra parameters to the west tool
    if build_type_args or cmake_args:
        build_cmd += " --"

    if build_type_args:
        build_cmd += f" {build_type_args}"

    if cmake_args:
        build_cmd += f" {clean_up_extra_args(cmake_args)}"

    return build_cmd


def run_job(east, progress, job, dry_run, verbose, spdx_app_only):
    """Runs the job with west.

    east ():            East context.
    job ():             Job to run.
    dry_run ():         If true then don't actually build, only show what commands
                        would run.
    verbose():          If true the Cmake output is shown.
    spdx_app_only():    If true then only apps are scanned for SPDX tags.

    Return:
        Bool            True, if job succeeded, false if it did not.
    """
    build_cmd = create_build_command(
        east,
        board=job["board"],
        build_type=job["build_type"],
        source_dir=job["src_dir"],
        silence_diagnostic=True,
    )

    if dry_run:
        east.print(
            f"[bold yellow]Dry running:[/] [dim italic]{build_cmd}[/]",
            highlight=False,
            soft_wrap=False,
            no_wrap=True,
            overflow="ignore",
            crop=False,
        )
        return

    # Handle any errors here, do not leave that to the east.run_west()
    kwargs = {"exit_on_error": False}

    if verbose:
        kwargs["silent"] = False
        kwargs["return_output"] = False
    else:
        kwargs["silent"] = True
        kwargs["return_output"] = True

    east.print(
        f"[bold green]Running:[/] [dim italic]{build_cmd}[/] ",
        highlight=False,
        soft_wrap=False,
        no_wrap=True,
        overflow="ignore",
        crop=False,
    )

    def on_failure(result):
        """Handle job failure."""
        if result["returncode"]:
            msg = (
                "Last build command [bold red]failed[/]! Check build log above"
                " to see what went wrong."
            )
            progress.stop()
            if not verbose:
                # Nicely print the build log, surounded by the rules and newlines for
                # paddings.
                east.print("")
                east.print(Rule(title="Captured build log", style="red"))
                east.print("")
                east.print(result["output"], **clean_print_args)
                east.print(Rule(title="Captured build log", style="red"))
                east.print("")
            east.print(Panel(msg, padding=1, border_style="red"))
            east.exit()

    if spdx_app_only and job["subdir"] == "apps":
        cmd = "spdx --init --build-dir build"
        result = east.run_west(cmd, **kwargs)
        on_failure(result)

    result = east.run_west(build_cmd, **kwargs)
    on_failure(result)

    if spdx_app_only and job["subdir"] == "apps":
        cmd = "spdx --build-dir build --analyze-includes --include-sdk"
        result = east.run_west(cmd, **kwargs)
        on_failure(result)


def check_if_single_app_repo():
    """Return True if this repo has just a single app project in the 'app' folder.

    Return False in any other case.
    """
    cmakelists = os.path.join("app", "CMakeLists.txt")

    # If there is no CMakeLists.txt file directly in the 'app' folder, than we are
    # certain that this is not a single app repo.
    if not os.path.isfile(cmakelists):
        return False

    # Only a "project(<something>)" is a valid indication that this is a single app repo,
    # CMakeLists without "project(<something>)" could still exist for some other
    # purpose.
    with open(cmakelists, "r") as f:
        for line in f:
            if re.match(r"project\(.*\)", line):
                return True
        return False


release_misuse_no_east_yml_msg = """
[bold yellow]east.yml[/] not found in project's root directory, [bold yellow]east release[/] needs it to determine required build steps, exiting!"""


def non_existing_app_msg_fmt(app_name):
    """Return a message."""
    return (
        f"Incorrect [bold yellow]east.yml[/], app [bold]{app_name}[/] was not"
        " found in app folder, exiting!"
    )


def non_existing_sample_msg_fmt(sample_name):
    """Return a message."""
    return (
        f"Incorrect [bold yellow]east.yml[/], sample [bold]{sample_name}[/] was not"
        " found in samples folder, exiting!"
    )


@click.command(**east_command_settings)
@click.option(
    "-d",
    "--dry-run",
    is_flag=True,
    help=(
        "Just echo build commands and create dummy artefacts, do not actually build."
        " Dummy artefacts are placed in into [bold italic]release_dry_run[/] folder. "
    ),
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Show west/Cmake build output. Default: false.",
)
@click.option(
    "--spdx-app-only",
    is_flag=True,
    help=(
        "Create an SPDX 2.2 tag-value bill of materials following the completion "
        "of a Zephyr build. This is done only for the apps, not for the samples."
    ),
)
@click.pass_obj
def release(east, dry_run, verbose, spdx_app_only):
    """Create a release folder with release artefacts.

    \b
    \n\n[bold yellow]east release[/] command runs a release process consisting of a series of [bold yellow]east build[/] commands to build applications and samples listed in the [bold yellow]east.yml[/]. Created build artefacts are then renamed and placed into [bold magenta]release[/] folder in project's root directory.

    \n\nVersion number is inferred from [bold italic cyan]git describe --tags --always --long --dirty=+[/] command. If the [bold yellow]east release[/] command is run directly on a commit with a version tag (such as [bold cyan]v1.0.2[/]), and there are no local changes, then only version tag is added to the name of artefacts, otherwise the additional git hash qualifier is added. If there is no version tag then default of [bold cyan]v0.0.0[/] is used.

    \n\nAs both [bold]apps[/] and [bold]samples[/] keys in [bold yellow]east.yml[/] are optional, release process for a specific key will be skipped, if it is not present.

    \n\nDifferent hardware versions of listed boards are picked up automatically from the `board` directory.

    \n\n[bold]Note:[/] This command requires [bold yellow]east.yml[/] to function.
    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check()

    if not east.east_yml:
        east.print(release_misuse_no_east_yml_msg)
        east.exit()

    # Move into project directory, from now on all commands are run relative from this
    # location
    east.chdir(east.project_dir)

    # Clean up release folders.
    sh.rmtree("release", ignore_errors=True)
    sh.rmtree("release_dry_run", ignore_errors=True)

    # Get version from git describe command
    version = get_git_version(east)

    if dry_run:
        release_dir = "release_dry_run"
    else:
        release_dir = "release"

    # Try to get apps and samples that need to be build, if some key is not found the
    # entire release process for it is skipped.

    # Update each dict in list with parent to indicate from where it came from.
    apps = east.east_yml.get("apps", [])
    samples = east.east_yml.get("samples", [])

    # Since above two return a reference to the array, we need to make a deep copy
    # to prevent any changes to the original dict.
    apps = copy.deepcopy(apps)
    samples = copy.deepcopy(samples)

    # We inject app and samples with additional key/value pairs in below two for loops
    # so the logic afterwards for detection of jobs can be common/simpler.
    # We also do some existence checks.

    # Small adjustment for projects which only have one single app.
    listed_apps = os.listdir("app") if os.path.isdir("app") else []

    # Magical heuristic to determine if this is single app repo or not.
    is_single_app = check_if_single_app_repo()

    # cleaned_apps is here just in case if there is no app key to prevent out of bounds
    # index access when doing apps[0]
    cleaned_apps = apps[0]["name"] if len(apps) else []
    apps_in_dir = cleaned_apps if is_single_app else listed_apps

    for app in apps:
        # Check, if the app even exists before building for it
        if app["name"] not in apps_in_dir:
            east.print(non_existing_app_msg_fmt(app["name"]))
            east.exit()
        # Add parent to mark from where this key comes from
        app.update({"parent": "apps"})
        # Add "release" type (but only in apps context).
        if "build-types" in app:
            app["build-types"].append({"type": "release"})
        else:
            app["build-types"] = [{"type": None}]

    for sample in samples:
        # Check, if the sample even exists before building for it
        if not os.path.isdir(os.path.join("samples", sample["name"])):
            east.print(non_existing_sample_msg_fmt(sample["name"]))
            east.exit()
        # Add parent to mark from where this key comes from
        sample.update({"parent": "samples"})
        # Add "release" build type which for samples does nothing.
        sample.update({"build-types": [{"type": None}]})

    # Apps and samples become targets, which can be handled in similar way.
    targets = apps + samples

    jobs = []
    for target in targets:
        for board in target["west-boards"]:
            for board in find_all_boards(east, board):
                # Extract build type names from dictionaries
                build_types = [x["type"] for x in target["build-types"]]
                for build_type in build_types:
                    # Rename created binaries and move them to a specific destination.
                    # Some dance around built type name is needed for "release" type

                    dst, src_dir = create_art_dest_and_src_dir(
                        target["name"],
                        target["parent"],
                        release_dir,
                        board,
                        build_type,
                        is_single_app,
                    )

                    # Create name for job artefact
                    name = create_artefact_name(
                        target["name"], board, version, build_type
                    )

                    # Create a job dict and add it to a list
                    job = {
                        # Subdir in release folder
                        "subdir": target["parent"],
                        # Source dir, used for build command
                        "src_dir": src_dir,
                        "board": board,
                        "build_type": build_type,
                        "artefact_name": name,
                        "artefact_destination": dst,
                    }
                    jobs.append(job)

    show_job_summary(east, jobs)

    east.print(Panel("[bold]Starting jobs[/]", border_style="green"))

    progress = Progress(
        SpinnerColumn(spinner_name="shark", style="blue", speed=0.5),
        TextColumn("[bold blue]Working ... "),
        BarColumn(style="dim", complete_style="green", finished_style="green"),
        TextColumn("[bold green]{task.completed} out of {task.total} jobs done[/]"),
        console=east.console,
    )

    with progress:
        task = progress.add_task("Running build commands...", total=len(jobs))
        for job in jobs:
            # Clean old build dir
            sh.rmtree("build", ignore_errors=True)

            # Run job build
            run_job(east, progress, job, dry_run, verbose, spdx_app_only)

            # Move and rename created artefacts
            move_build_artefacts(
                job["artefact_name"],
                job["artefact_destination"],
                job["subdir"],
                spdx_app_only,
                dry_run,
            )

            # Update progress
            progress.advance(task)

    # Construct git hash for zip names
    git_hash = f"-{version['hash']}" if version["hash"] else ""

    # First try to gather all zip targets and then execute them.
    zip_targets = []

    samples_folder = os.path.join(release_dir, "samples")
    if os.path.exists(samples_folder):
        zip_targets.append(
            {
                "name": f"samples-{version['tag']}{git_hash}",
                "folder": samples_folder,
            }
        )

    for app in apps:
        # Extract build type names from dictionaries
        build_types = [x["type"] for x in app["build-types"]]

        for build_type in build_types:
            # A bit of naming manipulation for release build
            if build_type:
                app_folder = os.path.join(release_dir, "apps", app["name"], build_type)
                build_type_suf = "" if build_type == "release" else f"-{build_type}"
            else:
                app_folder = os.path.join(release_dir, "apps", app["name"])
                build_type_suf = ""

            # Build zip name and make a zip archive
            zip_targets.append(
                {
                    "name": f"{app['name']}-{version['tag']}{build_type_suf}{git_hash}",
                    "folder": app_folder,
                }
            )

    # Execute all zip targets
    for zip_target in zip_targets:
        sh.make_archive(
            os.path.join(release_dir, zip_target["name"]),
            "zip",
            zip_target["folder"],
        )

    east.print(
        Panel(
            f"[bold]Done with jobs 🎉 \n\nCheck [magenta]{release_dir}[/] folder for"
            " artefacts.[/]",
            padding=1,
            border_style="green",
        )
    )
