import json
import os
import shutil as sh
from typing import Sequence

import click

from ..constants import EAST_GITHUB_URL
from ..east_context import east_command_settings
from ..helper_functions import determine_version_string
from ..modules.artifact import Artifact, ExtraArtifact, TwisterArtifact
from ..modules.artifacts2pack import ArtifactsToPack
from ..modules.tsuite import TSuite

no_east_yml_msg = """[bold yellow]east.yml[/] not found in project's root directory, [bold yellow]east pack[/] needs it to determine what to pack, exiting!"""


@click.option(
    "-t",
    "--twister-out-path",
    type=str,
    default="twister-out",
    help=(
        "Path to the twister-out directory from which to copy files from. Default: [bold cyan]twister-out[/]."
    ),
)
@click.option(
    "--tag",
    type=str,
    help="The tag to use for version information in the format "
    "v<MAJOR>.<MINOR>.<PATCH>[-<EXTRA>][+<TWEAK>], eg. [bold yellow]v1.2.3[/], "
    "[bold yellow]v1.2.3+4[/] or [bold yellow]v1.2.3-rc1+4[/]. "
    "If not provided, the tag will be determined using git describe.",
)
@click.option(
    "-p",
    "--pack-path",
    type=str,
    default="package",
    help=("Path to the generated directory. Default: [bold cyan]package[/]."),
)
@click.option(
    "-v",
    "--verbose",
    type=bool,
    is_flag=True,
    default=False,
    help="Enable verbose output.",
)
@click.command(**east_command_settings)
@click.pass_obj
def pack(east, twister_out_path: str, pack_path: str, tag: str, verbose: bool):
    """Create a release package from twister-generated build folders and other extra files.

    \b
    \n\nIn short, this command will:

    \n\n1. Check [bold yellow]east.yml[/] to see which files are relevant for the release.
    \n\n2. Copy those files from the Twister output to the [bold cyan]package[/] directory.
    \n\n3. Rename the files to include the project name and version.
    \n\n4. Copy any extra files specified in [bold yellow]east.yml[/] to [bold cyan]package/extra[/].
    \n\n5. Rename the extra files to include the version.
    \n\n6. Create ZIP files from the contents of the [bold cyan]package[/] directory.

    \b
    \n\n For details, see the documentation.

    \b
    \n\n[bold]Note:[/] This command requires [bold yellow]east.yml[/] with [bold yellow]pack[/] field to function.
    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    try:
        _pack(east, twister_out_path, pack_path, tag, verbose)
    except Exception as e:
        east.print(str(e))
        east.exit(1)


def _pack(east, twister_out_path: str, pack_path: str, tag: str, verbose: bool):
    east.pre_workspace_command_check()

    # Check that east.yml exists
    if not east.east_yml:
        raise Exception(no_east_yml_msg)

    # Check that twister_out_path exists
    if not os.path.exists(twister_out_path):
        raise Exception(
            f"[bold magenta]{twister_out_path}[/] directory couldn't be found from "
            "current working directory. \n"
        )

    # Check if twister_out contains twister.json (we need it to determine the testsuites)
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

    twister_artifacts = create_twister_artifacts(
        testsuites,
        atp,
        twister_out_path,
        pack_path,
        version_str,
    )
    # Perform checks specific for twister artifacts.
    check_that_specific_build_configs_exist_as_twister_artifacts(
        east, atp, twister_artifacts
    )
    check_that_all_twister_artifacts_exist(east, twister_artifacts)
    check_for_duplicated_twister_artifacts(twister_artifacts)

    extra_artifacts = create_extra_artifacts(atp, pack_path, version_str)

    # Perform checks specific for extra artifacts.
    check_that_all_extra_artifacts_exist(east, extra_artifacts)
    check_for_duplicated_extra_artifacts(east, extra_artifacts)

    # combine all artifacts
    # We must only use the common Artifacts methods from now on
    artifacts = twister_artifacts + extra_artifacts

    # Time to do some filesystem operations.
    sh.rmtree(pack_path, ignore_errors=True)

    for a in artifacts:
        if verbose:
            print(f"Copying artifact {a.src} -> {a.dst}")
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


def create_twister_artifacts(
    testsuites: Sequence[TSuite],
    atp: ArtifactsToPack,
    twister_out_path: str,
    pack_path: str,
    version_str: str,
) -> Sequence["TwisterArtifact"]:
    """Create a list of TwisterArtifact objects."""

    # Since TwisterArtifact.list_from_parts in create_artifact() returns a list of
    # artifacts and we are using it in a list comprehension, we need to flatten the list
    # of lists to a single list.
    def create_artifact(ts: TSuite) -> Sequence["TwisterArtifact"]:
        return TwisterArtifact.list_from_parts(
            ts, atp, version_str, twister_out_path, pack_path
        )

    def flatten(xss):
        return [x for xs in xss for x in xs]

    return flatten([create_artifact(ts) for ts in testsuites])


def create_extra_artifacts(
    atp: ArtifactsToPack,
    pack_path: str,
    version_str: str,
) -> Sequence["ExtraArtifact"]:
    """Create a list of ExtraArtifact objects."""
    return ExtraArtifact.list_from_parts(atp.extra_artifacts, pack_path, version_str)


def check_for_duplicated_twister_artifacts(artifacts: Sequence[TwisterArtifact]):
    """Check if any of the artifacts are duplicated."""
    duplicates = Artifact.find_duplicates(artifacts)

    if len(duplicates) == 0:
        return

    raise Exception(
        f"Duplicated destination artifacts were generated.\n\n"
        "This shouldn't happen, please report this to East's bug tracker on "
        f"{EAST_GITHUB_URL}."
    )


def check_for_duplicated_extra_artifacts(east, artifacts: Sequence[ExtraArtifact]):
    """Check if any of the extra artifacts are duplicated."""
    duplicates = Artifact.find_duplicates(artifacts)

    if len(duplicates) == 0:
        return

    header = (
        "It looks like that the [bold magenta]pack.extra[/] field in your "
        "[bold yellow]east.yml[/] contains files with the same name, which is not allowed.\n"
        "All files must have unique names, even if they are in different directories.\n\n"
    )
    header += "The following extra artifacts have the same name:\n"
    east.print(header)

    msg = ""

    for i, da in enumerate(duplicates):
        msg += f"\t {i + 1}. destination path: [bold cyan]{da[0].dst}[/]\n"
        for a in da:
            msg += f"\t\t- {a.src}\n"

    msg += "\n\n"

    east.print(
        msg,
        soft_wrap=False,
        no_wrap=True,
        overflow="ignore",
        crop=False,
    )
    east.exit(1)


def check_that_specific_build_configs_exist_as_twister_artifacts(
    east, atp: ArtifactsToPack, artifacts: Sequence[TwisterArtifact]
):
    """Check if all specified build configurations with additional or overwritten artifacts exist inside the twister-out directory.

    It is expected that the below error message will be printed quite often, as
    it can be easy to misconfigure the pack field in the east.yml file.

    Therefore, the error message should be as informative as possible.
    """
    # atp.bc_artifacts.keys() must be found within all artifact.ts.name
    missing_bcs = [
        p for p in atp.bc_artifacts.keys() if p not in {a.ts.name for a in artifacts}
    ]
    if len(missing_bcs) == 0:
        return

    header = (
        "It looks like that the [bold magenta]pack[/] field in your "
        "[bold yellow]east.yml[/] file isn't correctly configured for the output "
        "generated by Twister.\n\n"
    )
    header += "The following build configurations in [bold yellow]east.yml[/] are not named correctly, since no generated build folder matches them:\n"

    east.print(header)

    msg = ""

    for bc in missing_bcs:
        msg += f"Project:\t[bold cyan]{bc}[/]\n"

    msg += "\n\n"

    east.print(
        msg,
        soft_wrap=False,
        no_wrap=True,
        overflow="ignore",
        crop=False,
    )
    east.exit(1)


def check_that_all_twister_artifacts_exist(east, artifacts: Sequence[TwisterArtifact]):
    """Check if all Twister artifacts exist in the filesystem.

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
    header += (
        "The following built build configurations are missing at least one file:\n"
    )

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


def check_that_all_extra_artifacts_exist(east, artifacts: Sequence[ExtraArtifact]):
    """Check if all extra artifacts exist in the filesystem.

    It is expected that the below error message will be printed quite often, as
    it can be easy to misconfigure the pack field in the east.yml file.

    Therefore, the error message should be as informative as possible.
    """
    missing_artifacts = [a for a in artifacts if not a.does_exist()]

    if not missing_artifacts:
        return ""

    header = (
        "It looks like that the [bold magenta]pack.extra[/] field in your "
        "[bold yellow]east.yml[/] file isn't correctly configured, or you forgot "
        "to generate the extra artifacts.\n\n"
    )
    header += "The following extra artifacts are missing:\n"

    east.print(header)

    msg = ""

    for a in missing_artifacts:
        msg += f"\t- [bold cyan]{a.src}[/]\n"

    east.print(
        msg,
        soft_wrap=False,
        no_wrap=True,
        overflow="ignore",
        crop=False,
    )
    east.exit(1)
