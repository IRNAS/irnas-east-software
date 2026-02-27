from typing import Any, NamedTuple

from ..constants import EAST_GITHUB_URL
from .batchfile import BatchFile


class Project(NamedTuple):
    """Project object representing a build configuration for a project."""

    name: str
    artifacts: list[str]
    nrfutil_flash_pack: bool
    # Batch files are are not explicitly defined in the east.yml file, but are
    # determined by looking at the output west flash --dry-run command.
    batch_files: list[BatchFile] = []


class ArtifactsToPack(NamedTuple):
    """ArtifactsToPack object represents the artifacts to be packed, specific to a
    project.
    """

    common_artifacts: list[str]
    projects: list[Project]
    extra_artifacts: list[str]

    @classmethod
    def from_east_yml(cls, east_yml: dict[str, Any]):
        """Create an ArtifactsToPack object from the 'pack' field of east.yml."""
        if "pack" not in east_yml:
            raise Exception(
                "The [bold magenta]pack[/] field is missing from the "
                "[bold yellow]east.yml[/] file. Add it and try again."
            )

        pack = east_yml["pack"]
        common_artifacts = pack.get("artifacts", [])
        build_configs = pack.get("build_configurations", [])
        extra_artifacts = pack.get("extra", [])

        projects = []

        for bc in build_configs:
            if "artifacts" in bc:
                artifacts = common_artifacts + bc["artifacts"]
            elif "overwrite_artifacts" in bc:
                artifacts = bc["overwrite_artifacts"]
            else:
                raise Exception(
                    "One of 'artifact' or 'overwrite_artifact' keys must be present in "
                    "the project.\n\nThis shouldn't happen. Please report this "
                    f"to East's bug tracker on {EAST_GITHUB_URL}."
                )

            projects.append(
                Project(
                    name=bc["name"],
                    artifacts=artifacts,
                    nrfutil_flash_pack=bc.get("nrfutil_flash_pack", False),
                )
            )

        return cls(common_artifacts, projects, extra_artifacts)

    def get_artifacts_for_project(self, project: str) -> list[str]:
        """Return a list of artifacts for a given project.

        If that project is not found, return the common artifacts.
        """
        for p in self.projects:
            if p.name == project:
                return p.artifacts

        return self.common_artifacts

    def get_batch_files_for_project(self, project: str) -> list[BatchFile]:
        """Return a list of BatchFile objects for a given project.

        If that project is not found, return an empty list.
        """
        for p in self.projects:
            if p.name == project:
                return p.batch_files

        return []

    def if_has_project(self, project: str) -> bool:
        """Return whether the given project is defined in the ArtifactsToPack object."""
        for p in self.projects:
            if p.name == project:
                return True

        return False

    def uses_nrfutil_flash_packing(self, project: str) -> bool:
        """Return whether the given project should be packed using nrfutil flash packing."""
        for p in self.projects:
            if p.name == project:
                return p.nrfutil_flash_pack

        return False
