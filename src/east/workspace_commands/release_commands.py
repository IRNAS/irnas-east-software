import os
import shutil as sh

import click

from ..east_context import east_command_settings
from ..helper_functions import find_all_boards
from .basic_commands import build_command

BUILD_DIR = os.path.join("build", "zephyr")

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
    build_type = f"-{build_type}" if build_type else ""
    git_hash = f"-{version['hash']}" if version["hash"] else ""

    return f"{project}-{board}-{version['tag']}{build_type}{git_hash}"


def move_build_artefacts(art_name, art_dest, dry_run):
    """
    Moves build artefacts to art_dest and renames them to art_name.
    """

    # Create artefact destination
    os.makedirs(art_dest, exist_ok=True)

    binaries = ["app_update.bin", "merged.hex", "zephyr.elf"]

    for binary in binaries:
        exten = binary.split(".")[1]
        bin_path = os.path.join(BUILD_DIR, binary)

        # If doing dry run or running tests we just create empty files so that we have
        # something to copy
        if dry_run or RUNNING_TESTS:
            os.makedirs(BUILD_DIR, exist_ok=True)
            open(bin_path, "w").close()

        # app_update.bin and merged.hex are created only if building a DFU image
        if os.path.isfile(bin_path):
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
        if output[1] == "0" and not output[2].endwith("+"):
            # Clean version commit, no hash needed
            version = {"tag": output[0], "hash": ""}
        else:
            # Not on commit or dirty, both version and hash are needed
            version = {"tag": output[0], "hash": output[2]}

    else:
        east.print(
            f"Unsupported git describe output ({result['output']}), contact developer!"
        )
        east.exit()

    return version


release_misuse_no_east_yml_msg = """
[bold yellow]east.yml[/] not found in project's root directory, [bold yellow]east release[/] needs it to determine required build steps, exiting!"""


@click.command(**east_command_settings)
@click.option(
    "-d",
    "--dry-run",
    is_flag=True,
    help="Just echo build commands and create dummy artefacts, do not actually build.",
)
@click.pass_obj
def release(east, dry_run):
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

    east.chdir(east.project_dir)

    # Clean up release folder.
    sh.rmtree("release", ignore_errors=True)

    # Get version from git describe command
    version = get_git_version(east)

    # Try to get apps and samples that need to be build, if some key is not found the
    # entire release process for it is skipped.
    apps = east.east_yml.get("apps", [])
    samples = east.east_yml.get("samples", [])

    # Release process for applications:
    # for each application:
    #   for each west_board:
    #     for each of its hardware revisions:
    #       for every build type:
    #         Run west build command with correct conf files
    #         Create release subfolder with binaries
    #
    # for each application:
    #   for every build type:
    #     Create a zip folder
    for app in apps:
        for board in app["west-boards"]:
            for board_hv in find_all_boards(east, board):
                # Add None which is really "release" type
                build_types = app["build-types"] + [{"type": None}]
                for bt in build_types:
                    # Handle source_dir path differently if we have one or more apps
                    src_dir = "app"
                    if len(east.east_yml["apps"]) > 1:
                        src_dir = os.path.join(src_dir, app["name"])

                    # Clean old build dir
                    sh.rmtree("build", ignore_errors=True)

                    # Run build
                    print("Starting build command")
                    build_command(
                        east,
                        board=board_hv,
                        build_type=bt["type"],
                        source_dir=src_dir,
                        dry_run=dry_run,
                        be_silent_and_return=False,
                    )

                    # Rename created binaries and move them to a specific destination.
                    # Some dance around built type name is needed for "release" type
                    name = app["name"]
                    bt_art_dest = bt["type"] if bt["type"] else "release"
                    bt_art_name = bt["type"] if bt["type"] else ""
                    art_dest = os.path.join("release", "apps", name, bt_art_dest, board)
                    art_name = create_artefact_name(name, board, version, bt_art_name)
                    move_build_artefacts(art_name, art_dest, dry_run)

        # When everything is built for a specific app make zips.
        for bt in build_types:
            # A bit of naming manipulation for release build
            build_type = bt["type"] if bt["type"] else "release"
            folder_to_zip = os.path.join("release", "apps", app["name"], build_type)
            build_type_suf = f"-{bt['type']}" if bt["type"] else ""

            # Handle git hash
            git_hash = f"-{version['hash']}" if version["hash"] else ""

            # Build zip name and make a zip archive
            zip_name = f"{app['name']}-{version['tag']}{build_type_suf}{git_hash}"
            sh.make_archive(os.path.join("release", zip_name), "zip", folder_to_zip)

    # Release process for samples:
    # for each samples:
    #   for each west_board
    #     for each of its hardware revisions
    #         Run west build command with correct conf files
    #         And move them to a specific place
    for sample in samples:
        for board in sample["west-boards"]:
            for board_hv in find_all_boards(east, board):
                src_dir = os.path.join("samples", sample["name"])

                # Clean old build dir
                sh.rmtree("build", ignore_errors=True)

                # Run build
                print("Starting build command")
                build_command(
                    east,
                    board=board_hv,
                    source_dir=src_dir,
                    dry_run=dry_run,
                    be_silent_and_return=False,
                )

                # Rename created binaries and move them to a specific destination.
                name = sample["name"]
                art_dest = os.path.join("release", "samples", name, board)
                art_name = create_artefact_name(name, board, version, "")
                move_build_artefacts(art_name, art_dest, dry_run)

    if samples:
        folder_to_zip = os.path.join("release", "samples")

        # Handle git hash
        git_hash = f"-{version['hash']}" if version["hash"] else ""

        # Build zip name and make a zip archive
        zip_name = f"samples-{version['tag']}{git_hash}"
        sh.make_archive(os.path.join("release", zip_name), "zip", folder_to_zip)
