import json
import os
import shutil

import click

from ..constants import EAST_GITHUB_URL
from ..east_context import east_command_settings
from ..helper_functions import find_app_build_dir


class TSuiteError(Exception):
    """Exception raised when a TSuite object is not in a valid state."""

    pass


class TSuite:
    """TSuite object that represents a single testsuite in twister.json.

    The class name is intentionally shortened to TSuite to avoid pytest's automatic test
    discovery.
    """

    def __init__(self, name: str, board: str, twister_out_path: str, pack_path: str):
        # Name of the testsuite, e.g., app.prod, samples.blinky
        self.name = name
        # Normalized board name, e.g., nrf52840dk_nrf52840 or nrf52840dk@1.0.0_nrf52840
        self.board = board
        # Path to the testsuite's build directory inside the twister_out directory.
        self.twister_out_path = twister_out_path
        # Path to the testsuite's build directory inside the pack directory.
        self.pack_path = pack_path

    @classmethod
    def from_dict(cls, d: dict):
        """Create a TSuite object from a testsuite dictionary."""
        # WARN: All fields, that are accessed, should be checked for existence.
        required_keys = set(["name", "platform", "run_id", "status"])

        if not required_keys.issubset(d.keys()):
            msg = (
                f"The following testsuite json: \n\n{d}\n\n in "
                f"<twister_out>/twister.json is missing one or more of the following "
                "keys: {required_keys}.\n\nThis shouldn't happen. Please report this "
                f"to East's bug tracker on {EAST_GITHUB_URL}."
            )
            raise TSuiteError(msg)

        if d["status"] != "passed":
            msg = (
                f"'status' field for testsuite with name {d['name']} is {d['name']}, "
                "not 'passed'. \nYour <twister_out>/twister.json file contains "
                "unsuccesful runs. Please check the output of the twister command and "
                "try again."
            )
            raise TSuiteError(msg)

        board = d["platform"].replace("/", "_")
        name = os.path.basename(d["name"])

        return cls(
            name,
            board=board,
            twister_out_path=os.path.join(board, d["name"]),
            pack_path=os.path.join(name, board),
        )


class ArtifactsToPack:
    def __init__(
        self, common_artifacts: list[str], proj_artifacts: dict[str, list[str]]
    ):
        self.common_artifacts = common_artifacts
        self.proj_artifacts = proj_artifacts

    @classmethod
    def from_east_yml_pack_field(cls, east_yml_pack_field: dict[str, any]):
        common_artifacts = east_yml_pack_field.get("artifacts", [])
        projects = east_yml_pack_field["projects"]

        proj_artifacts = {}

        for p in projects:
            if "artifacts" in p:
                proj_artifacts[p["name"]] = common_artifacts + p["artifacts"]

            elif "overwrite_artifacts" in p:
                proj_artifacts[p["name"]] = p["overwrite_artifacts"]
            else:
                assert False, (
                    "One of 'artifact' or 'overwrite_artifact' keys must be present in "
                    "the project.\n\nThis shouldn't happen. Please report this "
                    f"to East's bug tracker on {EAST_GITHUB_URL}."
                )

        return cls(common_artifacts, proj_artifacts)

    def get_artifacts_for_project(self, project: str) -> list[str]:
        """Return a list of artifacts for a given project.

        If that project is not found, return the common artifacts.
        """
        return self.proj_artifacts.get(project, self.common_artifacts)


class Artifacts:
    def __init__(self, src_dir: str, raw_artifact_paths: list[str], dst_dir: str):
        # TODO: reorder args?

        self.artifact_files = [
            a.replace("$APP_DIR", find_app_build_dir(src_dir))
            for a in raw_artifact_paths
        ]

        self.src_dir_pairs = []

        for src, dst in zip(self.artifact_files, self.rename(self.artifact_files)):
            src = os.path.join(src_dir, src)
            dst = os.path.join(dst_dir, dst)

            self.src_dir_pairs.append((src, dst))

    def copy(self):
        for src, dst in self.src_dir_pairs:
            shutil.copy(src, dst)

    # Note, this is meant to be a private method
    @classmethod
    def rename(cls, artifact_files: list[str]) -> list[str]:
        # TODO: Implement renaming schema logic

        return artifact_files


@click.command(**east_command_settings)
@click.pass_obj
def pack(east):
    """Pack pack.

    \b
    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """
    east.pre_workspace_command_check()

    # TODO: make this as an arg
    twister_out_path = "twister_out"

    # Check if twister_out exists
    twister_json_path = os.path.join(twister_out_path, "twister.json")

    with open(twister_json_path, "r") as f:
        twister_json = json.load(f)

    # 1. Generate a list of TestSuite objects from twister.json
    # TODO: Check for testsuites key in twister
    try:
        testsuites = map(TSuite.from_dict, twister_json["testsuites"])
    except TSuiteError as e:
        # TODO: make this nicer
        print(e)
        east.exit(1)

    atp = ArtifactsToPack.from_east_yml_pack_field(east.east_yml["pack"])

    all_artifacts = []
    for ts in testsuites:
        artifacts = Artifacts(
            ts.twister_out_path, atp.get_artifacts_for_project(ts.name), ts.pack_path
        )

        # Existence check
        # Renaming logic
        # Duplication check
        all_artifacts.append(artifacts)

        # You now have src_dir

        # Get dst_dir

        # Replace it in all artifacts relative paths
        # Add togeter paths to form a list of full paths for src

        # Implement renaming schema logic

    # WARN: You should do all non-filesystem modifications operations first and then
    # do the rest. So, first check everything and then do the copying.
    for artifacts in all_artifacts:
        artifacts.copy_and_rename()

    # 3. Generate a list of artifacts for each TestSuite to copy and rename. Expand
    # $APP_DIR to suitable dir path. At this
    # step you should also check if the artifacts are present in the twister_out, abort
    # if they aren't. Renaming logic should also use the output of version logic. Also
    # check that there are no duplicate artifacts in the output list.
    # 3. "Execute" each testsuite object:
    #     - Copy and rename the testsuite's list of artifacts to the pack directory

    # print(projects)
