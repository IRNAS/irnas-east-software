from typing import Any, NamedTuple

from ..constants import EAST_GITHUB_URL


class ArtifactsToPack(NamedTuple):
    """ArtifactsToPack object represents the artifacts to be packed, specific to a
    project.
    """

    common_artifacts: list[str]
    proj_artifacts: dict[str, list[str]]
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
        projects = pack.get("projects", [])
        extra_artifacts = pack.get("extra", [])

        proj_artifacts = {}

        for p in projects:
            if "artifacts" in p:
                proj_artifacts[p["name"]] = common_artifacts + p["artifacts"]
            elif "overwrite_artifacts" in p:
                proj_artifacts[p["name"]] = p["overwrite_artifacts"]
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
        return self.proj_artifacts.get(project, self.common_artifacts)
