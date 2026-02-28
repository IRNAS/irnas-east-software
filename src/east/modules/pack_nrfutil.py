import os
import re

from ..east_context import EastContext
from ..modules.artifacts2pack import ArtifactsToPack, Project
from ..modules.tsuite import TSuite
from .batchfile import BatchFile


def nrfutil_flash_packing(
    east: EastContext,
    testsuites: list[TSuite],
    atp: ArtifactsToPack,
    twister_out_path: str,
):
    """Pack the given test suites and extra artifacts using nrfutil flash packing."""
    projects = []

    for ts in testsuites:
        # We only want to process the testsuites that are in the atp. If a testsuite is
        # not in the atp, it means that it definitely doesn't have
        # nrfutil_flash_pack enabled.
        if not atp.if_has_project(ts.name):
            continue

        artifacts = atp.get_artifacts_for_project(ts.name)
        uses_nrfutil = atp.uses_nrfutil_flash_packing(ts.name)

        # Doesn't use nrfutil flash packing, we can just add it as is.
        if not uses_nrfutil:
            projects.append(
                Project(name=ts.name, artifacts=artifacts, nrfutil_flash_pack=False)
            )
            continue

        # This testsuite should be packed using nrfutil flash packing, we need to find
        # the list of artifacts that would be flashed if we were to flash this testsuite
        # and add them to the atp.

        # find build folder
        build_dir = os.path.join(twister_out_path, ts.twister_out_path)

        # run west flash --dry-run to find all the artifacts that would be flashed
        out = east.run_west(
            f"flash --dry-run --skip-rebuild -d {build_dir}",
            return_output=True,
            silent=True,
        )

        binary_files, ext_mem_cgs, batch_files = parse_dry_run_output(out["output"])

        # Parent is the full, absolute path to the build dir.
        parent = os.path.join(east.cwd, build_dir)

        # Change the paths of the binary files to be relative to the build dir.
        required_files = [os.path.relpath(rf, parent) for rf in binary_files]

        # Append to the existing artifacts
        artifacts += required_files
        artifacts += ext_mem_cgs

        artifacts = list(set(artifacts))  # Remove duplicates if any

        projects.append(
            Project(
                name=ts.name,
                artifacts=artifacts,
                nrfutil_flash_pack=True,
                batch_files=batch_files,
            )
        )

    new_atp = ArtifactsToPack(
        common_artifacts=atp.common_artifacts,
        projects=projects,
        extra_artifacts=atp.extra_artifacts,
    )

    return new_atp


def parse_dry_run_output(output: str) -> tuple[list[str], list[str], list[BatchFile]]:
    """Parse west flash dry-run output to extract required information.

    This function looks for lines in the output that match the pattern of an nrfutil
    command with x-execute-batch, extracts the batch file path and any external memory
    config file path, and then reads the batch file to find all firmware files that are
    referenced in it.
    """
    # Pattern to match x-execute-batch command line
    execute_batch_pattern = re.compile(
        r"nrfutil\s+--json\s+device\s+"
        r"(?:--x-ext-mem-config-file\s+(\S+)\s+)?"
        r"x-execute-batch\s+"
        r"--batch-path\s+(\S+)"
    )

    required_files = []
    batch_files = []
    ext_mem_cfgs = []

    for line in output.splitlines():
        match = execute_batch_pattern.search(line)
        if not match:
            continue

        ext_mem_cfg = match.group(1)
        batch_file = match.group(2)

        if ext_mem_cfg:
            ext_mem_cfgs.append(ext_mem_cfg)

        # Extract just the filename for the ext-mem-config association.
        ext_mem_cfg_name = os.path.basename(ext_mem_cfg) if ext_mem_cfg else None

        bf = BatchFile.from_path(batch_file, ext_mem_config_name=ext_mem_cfg_name)
        batch_files.append(bf)

        # Read the batch file to find firmware files
        required_files += bf.get_fw_files()

    return required_files, ext_mem_cfgs, batch_files
