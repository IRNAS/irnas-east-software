import json
import os
import shutil as sh
from typing import Sequence

import click

from ..constants import EAST_GITHUB_URL
from ..east_context import east_command_settings
from ..helper_functions import determine_version_string
from ..modules.artifact import Artifact, ExtraArtifact, TwisterArtifact, WriteArtifact
from ..modules.artifacts2pack import ArtifactsToPack
from ..modules.batchfile import BatchFile
from ..modules.nrfutil_scripts import (
    generate_flash_script_bash,
    generate_flash_script_bat,
    generate_readme,
    generate_setup_script_bash,
    generate_setup_script_bat,
    get_all_helper_scripts_bash,
    get_all_helper_scripts_bat,
)
from ..modules.pack_nrfutil import nrfutil_flash_packing
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

    \b
    \n1. Check [bold yellow]east.yml[/] to see which files are relevant for the release.
    \n2. Copy those files from the Twister output to the [bold cyan]package[/] directory.
    \n3. Rename the files to include the project name and version.
    \n4. Copy any extra files specified in [bold yellow]east.yml[/] to [bold cyan]package/extra[/].
    \n5. Rename the extra files to include the version.
    \n6. Create ZIP files from the contents of the [bold cyan]package[/] directory.

    \b
    \n\nIf you set [bold yellow]nrfutil_flash_pack[/] to true for any of the projects in [bold yellow]east.yml[/], the command will also provide a self-contained flash package generated alongside the normal pack output. This package allows users to flash firmware using only the [bold magenta]nrfutil[/] binary, without needing east, west, or Zephyr installed.

    \n\nFor details, see the documentation.

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

    testsuites = TSuite.list_from_twister_json(twister_json, twister_out_path)
    atp = ArtifactsToPack.from_east_yml(east.east_yml)

    check_for_failed_testsuites(testsuites)

    version_str = determine_version_string(east, tag)

    atp = nrfutil_flash_packing(east, testsuites, atp, twister_out_path)

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

    batch_artifacts, updated_batch_files = create_batch_file_artifacts(
        twister_artifacts, atp
    )

    script_artifacts = create_nrfutil_script_artifacts(
        twister_artifacts, atp, updated_batch_files
    )

    # Perform checks specific for extra artifacts.
    check_that_all_extra_artifacts_exist(east, extra_artifacts)
    check_for_duplicated_extra_artifacts(east, extra_artifacts)

    # combine all artifacts
    # We must only use the common Artifacts methods from now on
    artifacts = twister_artifacts + extra_artifacts + batch_artifacts + script_artifacts

    # Time to do some filesystem operations.
    sh.rmtree(pack_path, ignore_errors=True)

    p_args = {
        "overflow": "ignore",
        "crop": False,
        "highlight": False,
        "soft_wrap": False,
        "no_wrap": True,
    }
    for a in artifacts:
        if verbose:
            east.print(f"[bold green]Copying:[/] {os.path.basename(a.dst)}", **p_args)
        a.copy()

    zip_targets = os.listdir(pack_path)

    for z in zip_targets:
        in_folder = os.path.join(pack_path, z)
        out_zip = os.path.join(pack_path, f"{z}-{version_str}")
        if verbose:
            east.print(f"[bold cyan]Creating ZIP:[/] {out_zip}.zip", **p_args)

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


def create_batch_file_artifacts(
    artifacts: Sequence["TwisterArtifact"], atp: ArtifactsToPack
) -> tuple[Sequence["WriteArtifact"], dict[str, list["BatchFile"]]]:
    """Create a list of WriteArtifact objects for the batch files.

    Content of the batch files is updated to match the renamed artifacts. The
    destination of the batch files is also updated to be in the same folder as the
    renamed artifacts.

    Returns:
        A tuple of:
        - List of WriteArtifact objects for the batch files.
        - Dict mapping project name to its list of updated BatchFile objects
          (with renamed firmware paths and ext_mem_config_name preserved).
    """
    write_artifacts = []
    updated_batch_files: dict[str, list["BatchFile"]] = {}

    for p in atp.projects:
        if not p.batch_files:
            continue

        updated_bfs = []
        for bf in p.batch_files:
            arts = [a for a in artifacts if a.ts.name == p.name]

            # Scan through arts, if their src appears in the content of the batch file,
            # replace it with the renamed name.
            for a in arts:
                bf = bf.update_matching_fw_file(a.src, a.renamed_name)

            # Since all artifacts in arts come from the same project, we can just take
            # the dst of the first
            dir = os.path.dirname(arts[0].dst)
            dst = os.path.join(dir, bf.name)
            write_artifacts.append(WriteArtifact(content=bf.content, dst=dst))
            updated_bfs.append(bf)

        updated_batch_files[p.name] = updated_bfs

    return write_artifacts, updated_batch_files


def create_nrfutil_script_artifacts(
    artifacts: Sequence["TwisterArtifact"],
    atp: ArtifactsToPack,
    updated_batch_files: dict[str, list[BatchFile]],
) -> list[WriteArtifact]:
    """Create WriteArtifact objects for nrfutil flash scripts and README.

    For each project with nrfutil_flash_pack enabled, generates:
    - linux/nrfutil_setup.sh, flash.sh, erase.sh, reset.sh, recover.sh
    - windows/nrfutil_setup.bat, flash.bat, erase.bat, reset.bat, recover.bat
    - README.md (in the build output root)

    Args:
        artifacts: List of TwisterArtifact objects (used to determine output directories).
        atp: ArtifactsToPack with project definitions.
        updated_batch_files: Dict mapping project name to updated BatchFile objects
            (with renamed firmware paths and ext_mem_config_name set).
    """
    script_artifacts: list[WriteArtifact] = []

    for p in atp.projects:
        if not p.nrfutil_flash_pack:
            continue

        batch_files = updated_batch_files.get(p.name, [])
        if not batch_files:
            continue

        # Determine the output directory from the first artifact for this project.
        project_arts = [a for a in artifacts if a.ts.name == p.name]
        if not project_arts:
            continue
        out_dir = os.path.dirname(project_arts[0].dst)

        # Extract device version from the first batch file. All batch files
        # produced by west flash contain the nrfutil_device_version field.
        device_version = batch_files[0].get_device_version()
        if device_version is None:
            raise Exception(
                f"Batch file [bold magenta]{batch_files[0].name}[/] for project "
                f"[bold cyan]{p.name}[/] is missing the "
                "[bold yellow]nrfutil_device_version[/] field. "
                "This field is expected in all batch files generated by west flash."
            )

        linux_dir = os.path.join(out_dir, "linux")
        windows_dir = os.path.join(out_dir, "windows")

        # Setup scripts
        script_artifacts.append(
            WriteArtifact(
                content=generate_setup_script_bash(),
                dst=os.path.join(linux_dir, "nrfutil_setup.sh"),
                executable=True,
            )
        )
        script_artifacts.append(
            WriteArtifact(
                content=generate_setup_script_bat(),
                dst=os.path.join(windows_dir, "nrfutil_setup.bat"),
            )
        )

        # Flash scripts
        script_artifacts.append(
            WriteArtifact(
                content=generate_flash_script_bash(batch_files, device_version),
                dst=os.path.join(linux_dir, "flash.sh"),
                executable=True,
            )
        )
        script_artifacts.append(
            WriteArtifact(
                content=generate_flash_script_bat(batch_files, device_version),
                dst=os.path.join(windows_dir, "flash.bat"),
            )
        )

        # Helper scripts (erase, reset, recover)
        for filename, content in get_all_helper_scripts_bash(device_version).items():
            script_artifacts.append(
                WriteArtifact(
                    content=content,
                    dst=os.path.join(linux_dir, filename),
                    executable=True,
                )
            )
        for filename, content in get_all_helper_scripts_bat(device_version).items():
            script_artifacts.append(
                WriteArtifact(
                    content=content,
                    dst=os.path.join(windows_dir, filename),
                )
            )

        # README
        script_artifacts.append(
            WriteArtifact(
                content=generate_readme(),
                dst=os.path.join(out_dir, "README.md"),
            )
        )

    return script_artifacts


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
    project_names = [p.name for p in atp.projects]
    missing_project_names = [
        p for p in project_names if p not in {a.ts.name for a in artifacts}
    ]
    if len(missing_project_names) == 0:
        return

    header = (
        "It looks like that the [bold magenta]pack[/] field in your "
        "[bold yellow]east.yml[/] file isn't correctly configured for the output "
        "generated by Twister.\n\n"
    )
    header += "The following build configurations in [bold yellow]east.yml[/] are not named correctly, since no generated build folder matches them:\n"

    east.print(header)

    msg = ""

    for bc in missing_project_names:
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
