from typing import Any, NamedTuple

from ..constants import EAST_GITHUB_URL


class ArtifactsToPack(NamedTuple):
    """ArtifactsToPack object represents the artifacts to be packed, specific to a
    project.
    """

    common_artifacts: list[str]
    bc_artifacts: dict[str, list[str]]
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

        proj_artifacts = {}

        for bc in build_configs:
            if "artifacts" in bc:
                proj_artifacts[bc["name"]] = common_artifacts + bc["artifacts"]
            elif "overwrite_artifacts" in bc:
                proj_artifacts[bc["name"]] = bc["overwrite_artifacts"]
            else:
                raise Exception(
                    "One of 'artifact' or 'overwrite_artifact' keys must be present in "
                    "the project.\n\nThis shouldn't happen. Please report this "
                    f"to East's bug tracker on {EAST_GITHUB_URL}."
                )

        return cls(common_artifacts, proj_artifacts, extra_artifacts)

    def get_artifacts_for_project(self, project: str) -> list[str]:
        """Return a list of artifacts for a given project.

        If that project is not found, return the common artifacts.
        """
        return self.bc_artifacts.get(project, self.common_artifacts)
