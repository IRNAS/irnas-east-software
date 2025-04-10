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
    def find_duplicates(cls, artifacts: Sequence["Artifact"]) -> Sequence[Sequence["Artifact"]]:
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
    """Artifact object based on twister generated build folders."""

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
            f"TwisterArtifact(src={self.src}, dst={self.dst}, ts={self.ts.name}, "
            f"raw_name={self.raw_name}, name={self.name}, renamed_name={self.renamed_name})"
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

        def create_artifact(raw_name: str) -> Artifact:
            name = raw_name.replace("$APP_DIR/", replace_text)
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
        """Rename twister artifact files by applying artifact renaming schema.

        Artifact renaming schema:

            <project_name>-[dirs-]<filename>-<version_str>.<ext>

        Where:
            project_name:       Name of the project, more specifically the name of the
                                project's build directory as output by the twister,
                                e.g., samples.blinky, app.prod, etc.
            dirs:               Directories in the path to the artifact file. Optional,
                                see below.
            filename:           Unmodified filename of the artifact.
            version_str:        Version string, as determined by the east gen-version
                                command.
            ext:                Unmodified file extension of the artifact.

        The 'dirs' part is optional and is determined by the path to the artifact file
        and its application build directory. The intention is to use 'dirs' part only
        for the cases where artifacts don't reside in the commonly used locations.

        The `dirs` part is omitted completely if the artifact is located directly in:
          * The project's build directory.
          * The `zephyr` directory in Sysbuild's default applications's build directory,
            eg. under "$APP_DIR/zephyr".

        If artifact is located directly in `zephyr` directory of some non-default
        application project, the 'dirs' part contains only the name of that non-default
        application project. For example, for "mcuboot/zephyr/zephyr.hex" the 'dirs' is
        just "mcuboot".

        For all other cases, the 'dirs' part contains the full path to the artifact file,
        relative to the project's build directory, with slashes replaced by dots.

        Examples:
        For:
            $APP_DIR = "blinky"
            project_name = "blinky.prod"
            version_str = "v1.0.0"

        The following artifacts:
            - blinky/zephyr/zephyr.hex
            - mcuboot/zephyr/zephyr.hex
            - blinky/Kconfig/Kconfig.dts
            - dfu_application.zip
            - merged.hex
            - blinky/zephyr/arch/cmake_install.cmake
            - mcuboot/zephyr/arch/cmake_install.cmake

        are renamed to:
            - blinky.prod-zephyr-v1.0.0.hex
            - blinky.prod-mcuboot-zephyr-v1.0.0.hex
            - blinky.prod-blinky.Kconfig-Kconfig-v1.0.0.dts
            - blinky.prod-dfu_application-v1.0.0.zip
            - blinky.prod-merged-v1.0.0.hex
            - blinky.prod-blinky.zephyr.arch-cmake_install-v1.0.0.cmake
            - blinky.prod-mcuboot.zephyr.arch-cmake_install-v1.0.0.cmake
        """
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

    Extra artifacts are not generated by twister, but are specified in the east.yml
    file under the 'pack.extra' field.
    """

    def __init__(self, src: str, dst: str):
        """Initialize the ExtraArtifact object."""
        super().__init__(src, dst)

    @classmethod
    def list_from_parts(
        cls, extra_artifacts: Sequence[str], pack_path: str, version_str: str,
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
        """Rename extra artifact files by applying artifact renaming schema.

        Artifact renaming schema:

            <filename>-<version_str>.<ext>

        Where:
            filename:           Unmodified filename of the artifact.
            version_str:        Version string, as determined by the east gen-version
                                command.
            ext:                Unmodified file extension of the artifact.

        Examples:
        For:
            src_full_path = "scripts/update_docker_version.sh"
            version_str = "v1.0.0"

        The resulting file name will be:
            update_docker_version-v1.0.0.sh
        """
        _, file = os.path.split(src_full_path)
        filename, ext = os.path.splitext(file)

        return f"{filename}-{version_str}{ext}"
