import os
import shutil
from typing import Iterator, Sequence

from ..helper_functions import find_app_build_dir
from .artifacts2pack import ArtifactsToPack
from .tsuite import TSuite


class Artifact(object):
    """Artifact object that represents a single artifact that needs to be packed."""

    # Source path to the artifact.
    src: str
    # Destination path to the artifact.
    dst: str

    def __init__(self, src, dst):
        """Initialize the Artifact object."""
        self.src = src
        self.dst = dst

    def __repr__(self):
        """Return a string representation of the Artifact object."""
        return f"Artifact(src={self.src}, dst={self.dst})"

    def copy(self):
        """Copy the artifact from the source to the destination directory."""
        os.makedirs(os.path.dirname(self.dst), exist_ok=True)
        shutil.copy(self.src, self.dst)

    def does_exist(self) -> bool:
        """Check if the artifact file exists."""
        return os.path.exists(self.src)

    @classmethod
    def find_duplicates(
        cls, artifacts: Sequence["Artifact"]
    ) -> Sequence[Sequence["Artifact"]]:
        """Find artifacts with duplicate destination paths.

        Returns a list of lists, where each inner list contains artifacts with the same
        destination path.
        """
        duplicates = set()
        ret = []
        for art in artifacts:
            # skip artifacts that are already accounted for
            if art.dst in duplicates:
                continue
            # find all artifacts with the same destination path
            same_dst = [a for a in artifacts if a.dst == art.dst]
            if len(same_dst) > 1:
                duplicates.add(art.dst)
                ret.append(same_dst)

        return ret


class TwisterArtifact(Artifact):
    """Artifact object based on Twister generated build folders."""

    # Below fields are mostly used for diagnostic purposes.

    # Testsuite that Artifact belongs to.
    ts: TSuite
    # Name of the artifact, as given in the east.yml.
    raw_name: str
    # Name of the artifact after $APP_DIR is replaced.
    name: str
    # Name of the artifact after renaming.
    renamed_name: str

    def __init__(
        self,
        src: str,
        dst: str,
        ts: TSuite,
        raw_name: str,
        name: str,
        renamed_name: str,
    ):
        """Initialize the TwisterArtifact object."""
        super().__init__(src, dst)
        self.ts = ts
        self.raw_name = raw_name
        self.name = name
        self.renamed_name = renamed_name

    def __repr__(self):
        """Return a string representation of the TwisterArtifact object."""
        return (
            f"TwisterArtifact(\n"
            f"    src={self.src}, \n"
            f"    dst={self.dst}, \n"
            f"    ts={self.ts.name}, \n"
            f"    raw_name={self.raw_name}, \n"
            f"    name={self.name}, \n"
            f"    renamed_name={self.renamed_name}, \n"
            f")"
        )

    @classmethod
    def list_from_parts(
        cls,
        ts: TSuite,
        atp: ArtifactsToPack,
        version_str: str,
        twister_out_dir_path: str,
        pack_path: str,
        app_build_dirs: Iterator[str] | None = None,
    ) -> Sequence["TwisterArtifact"]:
        """Create a list of Artifact objects from various parts.

        All arguments, besides app_build_dirs, are required.

        The only reason that app_build_dirs is optional is to remove dependency on the
        filesystem access during testing (find_app_build_dir checks the content of the
        domain.yaml file).
        """
        src_dir = os.path.join(twister_out_dir_path, ts.twister_out_path)
        dst_dir = os.path.join(pack_path, ts.name, ts.board)

        # The app_build_dir must be relative to the src_dir.
        if app_build_dirs:
            app_build_dir = next(app_build_dirs)
        else:
            app_build_dir = os.path.relpath(find_app_build_dir(src_dir), src_dir)

        replace_text = "" if app_build_dir == "." else f"{app_build_dir}{os.sep}"

        raw_arts = atp.get_artifacts_for_project(ts.name)

        def create_artifact(raw_name: str) -> "TwisterArtifact":
            name = raw_name.replace("$APP_DIR/", replace_text)

            if os.path.isabs(name):
                # This is some file that is outside of the build dir, those ones are
                # are not renamed, but we still want to create an artifact for them, so
                # we just use the basename of the file as the renamed name.
                renamed_name = os.path.basename(name)
                src = name
                dst = os.path.join(dst_dir, renamed_name)
            else:
                renamed_name = cls._rename(name, ts.name, app_build_dir, version_str)
                src = os.path.join(src_dir, name)
                dst = os.path.join(dst_dir, renamed_name)

            art = cls(src, dst, ts, raw_name, name, renamed_name)

            return art

        return [create_artifact(a) for a in raw_arts]

    @classmethod
    def _rename(
        cls,
        artifact: str,
        project_name: str,
        app_build_dir: str,
        version_str: str,
    ) -> str:
        """Rename Twister artifact files by applying the Twister artifact renaming schema."""
        # Developer note: If this ever changes, please also update the schema description
        # in the documentation (docs/pack.md).

        dir, file = os.path.split(artifact)
        filename, ext = os.path.splitext(file)
        app_zephyr_dir = os.path.join(app_build_dir, "zephyr")

        if dir == app_zephyr_dir:
            dir = dir.replace(app_zephyr_dir, "")

        if os.path.basename(dir) == "zephyr":
            dir = dir.replace("zephyr", "")

        dir = dir.replace("//", "/").replace("/", ".").strip(".")

        if dir:
            dir = f"{dir}-"

        return f"{project_name}-{dir}{filename}-{version_str}{ext}"


class ExtraArtifact(Artifact):
    """Artifact object that represents an extra artifact that needs to be packed.

    Extra artifacts are not generated by Twister, but are specified in the east.yml
    file under the 'pack.extra' field.
    """

    def __init__(self, src: str, dst: str):
        """Initialize the ExtraArtifact object."""
        super().__init__(src, dst)

    @classmethod
    def list_from_parts(
        cls,
        extra_artifacts: Sequence[str],
        pack_path: str,
        version_str: str,
    ) -> Sequence["ExtraArtifact"]:
        """Create a list of ExtraArtifact objects from a list of paths.

        The list is usually the 'pack.extra' field from the east.yml file.
        """
        artifacts = []
        for ea in extra_artifacts:
            src = ea
            new_name = cls._rename(src, version_str)
            dst = os.path.join(pack_path, "extra", new_name)
            artifacts.append(cls(src, dst))

        return artifacts

    @classmethod
    def _rename(
        cls,
        src_full_path: str,
        version_str: str,
    ) -> str:
        """Rename extra artifact files by applying the extra artifact renaming schema."""
        # Developer note: If this ever changes, please also update the schema description
        # in the documentation (docs/pack.md).

        _, file = os.path.split(src_full_path)
        filename, ext = os.path.splitext(file)

        return f"{filename}-{version_str}{ext}"


class WriteArtifact(Artifact):
    """Artifact object that represents an artifact that needs to be written.

    This Artifact doesn't have a source, only content which was generated in some way
    and needs to be written to the destination path.
    """

    content: str
    executable: bool

    def __init__(self, content: str, dst: str, executable: bool = False):
        """Initialize the WriteArtifact object.

        @param content: The content to write to the file.
        @param dst: The destination path.
        @param executable: If True, set the executable permission bit after writing.
        """
        super().__init__(src="", dst=dst)
        self.content = content
        self.executable = executable

    def __repr__(self):
        """Return a string representation of the Artifact object."""
        repr = f"Artifact(src={self.src}\ndst={self.dst}\ncontent={self.content}\n)"
        return repr

    def copy(self):
        """Write the content to the destination path.

        Override the copy method to write the content to the destination path instead of
        copying.
        """
        os.makedirs(os.path.dirname(self.dst), exist_ok=True)
        with open(self.dst, "w") as f:
            f.write(self.content)
        if self.executable:
            os.chmod(self.dst, os.stat(self.dst).st_mode | 0o111)
