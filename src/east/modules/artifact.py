import os
import shutil
from typing import Iterator, NamedTuple, Sequence

from ..helper_functions import find_app_build_dir
from .artifacts2pack import ArtifactsToPack
from .tsuite import TSuite


class Artifact(NamedTuple):
    """Artifact object that represents a single artifact that needs to be packed."""

    # Source path to the artifact.
    src: str
    # Destination path to the artifact.
    dst: str

    # Below fields are mostly used for diagnostic purposes.

    # Testsuite that Artifact belongs to.
    ts: TSuite
    # Name of the artifact, as given in the east.yml.
    raw_name: str
    # Name of the artifact after $APP_DIR is replaced.
    name: str
    # Name of the artifact after renaming.
    renamed_name: str

    @classmethod
    def list_from_parts(
        cls,
        ts: TSuite,
        atp: ArtifactsToPack,
        version_str: str,
        twister_out_dir_path: str,
        pack_path: str,
        app_build_dirs: Iterator[str] | None = None,
    ) -> Sequence["Artifact"]:
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

    def copy(self):
        """Copy all artifacts from source to the destination directory."""
        os.makedirs(os.path.dirname(self.dst), exist_ok=True)
        shutil.copy(self.src, self.dst)

    def does_exist(self) -> bool:
        """Check if the aritfact file exists."""
        return os.path.exists(self.src)

    @classmethod
    def _rename(
        cls,
        artifact: str,
        project_name: str,
        app_build_dir: str,
        version_str: str,
    ) -> str:
        """Rename artifact files by applying artifact renaming schema.

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
