import json
import os
import shutil as sh
from typing import Sequence

import click

from ..constants import EAST_GITHUB_URL
from ..east_context import east_command_settings
from ..helper_functions import determine_version_string
from ..modules.artifact import Artifact
from ..modules.artifacts2pack import ArtifactsToPack
from ..modules.tsuite import TSuite


@click.option(
    "-t",
    "--twister-out-path",
    type=str,
    default="twister-out",
    help=("Path to the twister-out directory. Default: twister-out."),
)
@click.option(
    "--tag",
    type=str,
    help="The tag to use for version information in the format "
    "v<MAJOR>.<MINOR>.<PATCH>[-<EXTRA>][+<TWEAK>], eg. [bold yellow]v1.2.3[/], "
    "[bold yellow]v1.2.3+4[/] or [bold yellow]v1.2.3-rc1+4[/]. If this flag is given, "
    "the [bold cyan]east util version[/] command assumes that the git HEAD is on the "
    "tagged commit and that the repo is clean.",
)
@click.option(
    "-p",
    "--pack-path",
    type=str,
    default="package",
    help=("Path to the generated directory. Default: [bold cyan]package[/]."),
)
@click.command(**east_command_settings)
@click.pass_obj
def pack(east, twister_out_path: str, pack_path: str, tag: str):
    """Pack pack. TODO: add description.

    \b
    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    try:
        _pack(east, twister_out_path, pack_path, tag)
    except Exception as e:
        east.print(str(e))
        east.exit(1)


def _pack(east, twister_out_path: str, pack_path: str, tag: str):
    east.pre_workspace_command_check()

    if not os.path.exists(twister_out_path):
        raise Exception(
            f"[bold magenta]{twister_out_path}[/] directory couldn't be found from "
            "current working directory. \n"
        )

    # Check if twister_out exists
    try:
        with open(os.path.join(twister_out_path, "twister.json")) as f:
            twister_json = json.load(f)
    except FileNotFoundError:
        raise Exception(
            f"[bold magenta]twister.json[/] file was not found in the "
            f"{twister_out_path} directory. "
            "Run the [bold magenta]east twister[/] command and try again."
        )

    testsuites = TSuite.list_from_twister_json(twister_json)
    atp = ArtifactsToPack.from_east_yml(east.east_yml)

    check_for_failed_testsuites(testsuites)

    version_str = determine_version_string(east, tag)

    artifacts = create_artifacts(
        testsuites,
        atp,
        twister_out_path,
        pack_path,
        version_str,
    )

    check_for_duplicated_artifacts(artifacts)
    check_that_specific_projects_exist_as_artifacts(east, atp, artifacts)
    check_that_all_artifacts_exist(east, artifacts)

    # All possible checks succeeded, time to do some filesystem operations.
    sh.rmtree(pack_path, ignore_errors=True)

    for a in artifacts:
        a.copy()

    zip_targets = os.listdir(pack_path)

    for z in zip_targets:
        in_folder = os.path.join(pack_path, z)
        out_zip = os.path.join(pack_path, f"{z}-{version_str}")

        sh.make_archive(out_zip, "zip", in_folder)


def check_for_failed_testsuites(testsuites: Sequence[TSuite]):
    """Check if any of the testsuites did not build or failed, and raise an error if so."""
    failed_testsuites = [
        ts for ts in testsuites if not ts.did_build() and ts.did_fail()
    ]

    if failed_testsuites:
        list_of_bad_testsuites = "\n".join(
            [f"- {ts.name}, status: {ts.status}" for ts in failed_testsuites]
        )
        msg = (
            "Your <twister_out>/twister.json file contains failed runs: "
            f"{list_of_bad_testsuites}.\n\n"
            "Please check the mistakes in the above runs and then run "
            "[bold magenta]east twister[/] and [bold magenta]east pack[/] commands "
            "again."
        )
        raise Exception(msg)


def create_artifacts(
    testsuites: Sequence[TSuite],
    atp: ArtifactsToPack,
    twister_out_path: str,
    pack_path: str,
    version_str: str,
) -> Sequence["Artifact"]:
    """Create a list of Artifact objects."""

    # Since Artifact.list_from_parts in create_artifact() returns a list of
    # artifacts and we are using it in a list comprehension, we need to flatten the list
    # of lists to a single list.
    def create_artifact(ts: TSuite) -> Sequence["Artifact"]:
        return Artifact.list_from_parts(
            ts, atp, version_str, twister_out_path, pack_path
        )

    def flatten(xss):
        return [x for xs in xss for x in xs]

    return flatten([create_artifact(ts) for ts in testsuites])


def check_for_duplicated_artifacts(artifacts: Sequence[Artifact]):
    """Check if any of the artifacts are duplicated."""
    dsts = [a.dst for a in artifacts]

    if len(dsts) != len(set(dsts)):
        raise Exception(
            f"Duplicated destination artifacts were generated.\n\n"
            "This shouldn't happen, please report this to East's bug tracker on "
            f"{EAST_GITHUB_URL}."
        )


def check_that_specific_projects_exist_as_artifacts(
    east, atp: ArtifactsToPack, artifacts: Sequence[Artifact]
):
    """Check if all specified projects with extra or overwritten artifacts exist inside the twister-out directory.



    It is expected that the below error message will be printed quite often, as
    it can be easy to misconfigure the pack field in the east.yml file.

    Therefore, the error message should be as informative as possible.
    """
    # atp.proj_artifacts.keys() must be found within all artifact.ts.name
    missing_projects = [
        p for p in atp.proj_artifacts.keys() if p not in {a.ts.name for a in artifacts}
    ]
    if len(missing_projects) == 0:
        return

    header = (
        "It looks like that the [bold magenta]pack[/] field in your "
        "[bold yellow]east.yml[/] file isn't correctly configured for the output "
        "generated by Twister.\n\n"
    )
    header += "The following projects in [bold yellow]east.yml[/] are not named correctly, since no generated build folder matches them:\n"

    east.print(header)

    msg = ""

    for p in missing_projects:
        msg += f"Project:\t[bold cyan]{p}[/]\n"

    msg += "\n\n"

    east.print(
        msg,
        soft_wrap=False,
        no_wrap=True,
        overflow="ignore",
        crop=False,
    )
    east.exit(1)


def check_that_all_artifacts_exist(east, artifacts: Sequence[Artifact]):
    """Check if all artifacts exist inside the twister-out directory.

    It is expected that the below error message will be printed quite often, as
    it can be easy to misconfigure the pack field in the east.yml file.

    Therefore, the error message should be as informative as possible.
    """
    missing_artifacts = [a for a in artifacts if not a.does_exist()]

    if not missing_artifacts:
        return ""

    # Group the artifacts by their TSuite
    grouped_artifacts = {}
    for a in missing_artifacts:
        if a.ts not in grouped_artifacts:
            grouped_artifacts[a.ts] = []
        grouped_artifacts[a.ts].append(a)

    header = (
        "It looks like that the [bold magenta]pack[/] field in your "
        "[bold yellow]east.yml[/] file isn't correctly configured for the output "
        "generated by Twister.\n\n"
    )
    header += "The following build projects are missing atleast one file:\n"

    east.print(header)

    msg = ""

    for ts, artifacts in grouped_artifacts.items():
        msg += f"Project path:\t[bold cyan]{ts.path}[/]\n"
        msg += f"Testsuite:\t[bold cyan]{ts.name}[/]\n"
        msg += f"Board:\t\t[bold cyan]{ts.raw_board}[/]\n"
        msg += f"Build folder:\t[bold cyan]{ts.twister_out_path}[/]\n"

        if len(artifacts) > 1:
            msg += "Missing files:\t"
        else:
            msg += "Missing file:\t"

        for i, a in enumerate(artifacts):
            msg += f"[bold magenta]{a.name}[/]"
            if i != len(artifacts) - 1:
                msg += ", "

        msg += "\n\n"

    east.print(
        msg,
        soft_wrap=False,
        no_wrap=True,
        overflow="ignore",
        crop=False,
    )
    east.exit(1)
