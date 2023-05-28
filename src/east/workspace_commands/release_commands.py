import os
import shutil as sh

import click
from rich.box import ROUNDED
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..east_context import east_command_settings
from ..helper_functions import find_all_boards
from .basic_commands import create_build_command

# This could be considered as a hack, but it is actually the cleanest way to test
# release command.
RUNNING_TESTS = False


def create_artefact_name(project, board, version, build_type):
    """
    Create an artefact name.

    Board might be in form <west_board>@<hv_version>, in that case we modify it to fit
    the artefact name.

    We also add git hash at the end if the build was not done on the clean tagged
    commit.
    """
    board = board.replace("@", "-hv")

    # "release" or None build_type should not generate any build type qualifier.
    build_type = "" if build_type == "release" or not build_type else f"-{build_type}"

    git_hash = f"-{version['hash']}" if version["hash"] else ""

    return f"{project}-{board}-{version['tag']}{build_type}{git_hash}"


def move_build_artefacts(art_name, art_dest, dry_run):
    """
    Moves build artefacts to art_dest and renames them to art_name.
    """

    # Create artefact destination
    os.makedirs(art_dest, exist_ok=True)

    build_dir = os.path.join("build", "zephyr")

    # Determine, if we have basic build with MCUBoot, some other build with child images, or default build
    if (
        os.path.isfile(os.path.join(build_dir, "app_update.bin"))
        or dry_run
        or RUNNING_TESTS
    ):
        # MCUBoot
        binaries = ["dfu_application.zip", "app_update.bin", "merged.hex", "zephyr.elf"]
    elif os.path.isfile(os.path.join(build_dir, "merged.hex")):
        # Other (TFM, SPM, ...)
        binaries = ["merged.hex", "zephyr.elf"]
    else:
        # Basic build (No merged.hex is generated)
        binaries = ["zephyr.bin", "zephyr.hex", "zephyr.elf"]

    for binary in binaries:
        bin_path = os.path.join(build_dir, binary)

        # If doing dry run or running tests we just create empty files so that we have
        # something to copy
        if dry_run or RUNNING_TESTS:
            os.makedirs(build_dir, exist_ok=True)
            open(bin_path, "w").close()

        if os.path.isfile(bin_path):
            exten = binary.split(".")[1]
            sh.copyfile(
                bin_path,
                os.path.join(art_dest, ".".join([art_name, exten])),
            )


def get_git_version(east):
    """
    Return output from git describe command, see help string of release function for
    more information.
    """
    result = east.run(
        "git describe --tags --always --long --dirty=+", silent=True, return_output=True
    )

    output = result["output"].strip().split("-")

    if len(output) == 1:
        # No git tag, only hash was produced
        version = {"tag": "v0.0.0", "hash": output[0]}
    elif len(output) == 3:
        if output[1] == "0" and not output[2].endswith("+"):
            # Clean version commit, no hash needed
            version = {"tag": output[0], "hash": ""}
        else:
            # Not on commit or dirty, both version and hash are needed
            version = {"tag": output[0], "hash": output[2][1:]}

    else:
        east.print(
            f"Unsupported git describe output ({result['output']}), contact developer!"
        )
        east.exit()

    return version


def show_job_summary(east, jobs):
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


def run_job(east, progress, job, dry_run, verbose):
    """Runs the job with a west

    east ():            East context.
    job ():             Job to run.
    dry_run ():         If true then don't actually build, only show what commands
                        would run.
    verbose():          If true the Cmake output is shown.

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
    result = east.run_west(build_cmd, **kwargs)

    if result["returncode"]:
        # Build failed, report to the user.
        progress.stop()
        if not verbose:
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
            "Last build command [bold red]failed[/]! Check build output above"
            " to see what went wrong."
        )
        east.print(Panel(msg, padding=1, border_style="red"))
        east.exit()


release_misuse_no_east_yml_msg = """
[bold yellow]east.yml[/] not found in project's root directory, [bold yellow]east release[/] needs it to determine required build steps, exiting!"""


def non_existing_app_msg_fmt(app_name):
    return (
        f"Incorrect [bold yellow]east.yml[/], app [bold]{app_name}[/] was not"
        " found in app folder, exiting!"
    )


def non_existing_sample_msg_fmt(sample_name):
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
@click.pass_obj
def release(east, dry_run, verbose):
    """
    Create a release folder with release artefacts.

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

    # We inject app and samples with additional key/value pairs in below two for loops
    # so the logic afterwards for detection of jobs can be common/simpler.
    # We also do some existence checks.

    # Small adjustment for projects which only have one single app
    apps_in_dir = apps[0]["name"] if len(apps) == 1 else os.listdir("app")

    for app in apps:
        # Check, if the app even exists before building for it
        if app["name"] not in apps_in_dir:
            east.print(non_existing_app_msg_fmt(app["name"]))
            east.exit()
        # Add parent to mark from where this key comes from
        app.update({"parent": "apps"})
        # Add "release" type (but only in apps context).
        app["build-types"].append({"type": "release"})

    samples_in_dir = os.listdir("samples")
    for sample in samples:
        # Check, if the sample even exists before building for it
        if sample["name"] not in samples_in_dir:
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

                    common_dest = os.path.join(
                        release_dir, target["parent"], target["name"]
                    )

                    if target["parent"] == "apps":
                        # Create destination path where artefact should be placed into
                        destination = os.path.join(common_dest, build_type, board)
                        if len(apps) == 1:
                            src_dir = "app"
                        else:
                            src_dir = os.path.join("app", target["name"])

                    if target["parent"] == "samples":
                        # Create destination path where artefact should be placed into
                        destination = os.path.join(common_dest, board)
                        src_dir = os.path.join("samples", target["name"])

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
                        "artefact_destination": destination,
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
            run_job(east, progress, job, dry_run, verbose)

            # Move and rename created artefacts
            move_build_artefacts(
                job["artefact_name"], job["artefact_destination"], dry_run
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
            app_folder = os.path.join(release_dir, "apps", app["name"], build_type)

            build_type_suf = "" if build_type == "release" else f"-{build_type}"

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
