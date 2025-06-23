from east.modules.artifact import Artifact, ExtraArtifact, TwisterArtifact


def test_check_for_no_duplicate_artifacts():
    """Test that no duplicate artifacts are found in a list of artifacts.

    GIVEN a list of artifacts with no duplicate destination paths,
    WHEN checking for duplicate artifacts,
    THEN the returned list should be empty.
    """
    artifacts = [
        TwisterArtifact("", "dst1", None, "", "", ""),
        TwisterArtifact("", "dst2", None, "", "", ""),
        TwisterArtifact("", "dst3", None, "", "", ""),
        ExtraArtifact("", "dst4"),
    ]

    duplicates = Artifact.find_duplicates(artifacts)

    assert duplicates == []


def test_check_for_duplicate_artifacts():
    """Test that duplicate artifacts are found in a list of artifacts.

    GIVEN a list of artifacts with duplicate destination paths,
    WHEN checking for duplicate artifacts,
    THEN the returned list should contain the duplicate artifacts.
    """
    artifacts = [
        ExtraArtifact("", "dst1"),
        TwisterArtifact("", "dst2", None, "", "", ""),
        TwisterArtifact("", "dst3", None, "", "", ""),
        TwisterArtifact("", "dst2", None, "", "", ""),
        ExtraArtifact("", "dst1"),
    ]

    duplicates = Artifact.find_duplicates(artifacts)

    assert len(duplicates) == 2
    assert len(duplicates[0]) == 2
    assert len(duplicates[1]) == 2
    assert duplicates[0][0].dst == "dst1"
    assert duplicates[0][1].dst == "dst1"
    assert duplicates[1][0].dst == "dst2"
    assert duplicates[1][1].dst == "dst2"


def test_renaming_twister_artifacts_from_project_using_sysbuild():
    """Test renaming Twister artifacts from a project using sysbuild.

    GIVEN a list of Twister artifacts from a project using sysbuild,
    WHEN renaming Twister artifacts,
    THEN the returned list should contain the renamed Twister artifacts.
    """
    inputs = [
        "blinky/zephyr/zephyr.hex",
        "mcuboot/zephyr/zephyr.hex",
        "blinky/Kconfig/Kconfig.dts",
        "dfu_application.zip",
        "merged.hex",
        "blinky/zephyr/arch/cmake_install.cmake",
        "mcuboot/zephyr/arch/cmake_install.cmake",
    ]

    app_build_dir = "blinky"
    project_name = "blinky.prod"
    version_str = "v1.0.0"

    def rename(input):
        return TwisterArtifact._rename(input, project_name, app_build_dir, version_str)

    outputs = [rename(i) for i in inputs]

    assert outputs == [
        "blinky.prod-zephyr-v1.0.0.hex",
        "blinky.prod-mcuboot-zephyr-v1.0.0.hex",
        "blinky.prod-blinky.Kconfig-Kconfig-v1.0.0.dts",
        "blinky.prod-dfu_application-v1.0.0.zip",
        "blinky.prod-merged-v1.0.0.hex",
        "blinky.prod-blinky.zephyr.arch-cmake_install-v1.0.0.cmake",
        "blinky.prod-mcuboot.zephyr.arch-cmake_install-v1.0.0.cmake",
    ]


def test_renaming_twister_artifacts_from_project_not_using_sysbuild():
    """Test renaming artifacts from a project not using sysbuild.

    GIVEN a list of artifacts from a project using sysbuild,
    WHEN renaming artifacts,
    THEN the returned list should contain the renamed artifacts.
    """
    inputs = [
        "zephyr/zephyr.hex",
        "Kconfig/Kconfig.dts",
        "dfu_application.zip",
        "merged.hex",
        "zephyr/arch/cmake_install.cmake",
    ]

    app_build_dir = "."
    project_name = "blinky.prod"
    version_str = "v1.0.0"

    def rename(input):
        return TwisterArtifact._rename(input, project_name, app_build_dir, version_str)

    outputs = [rename(i) for i in inputs]

    assert outputs == [
        "blinky.prod-zephyr-v1.0.0.hex",
        "blinky.prod-Kconfig-Kconfig-v1.0.0.dts",
        "blinky.prod-dfu_application-v1.0.0.zip",
        "blinky.prod-merged-v1.0.0.hex",
        "blinky.prod-zephyr.arch-cmake_install-v1.0.0.cmake",
    ]


def test_renaming_extra_artifacts():
    """Test renaming extra artifacts.

    GIVEN a list of extra artifacts,
    WHEN renaming extra artifacts,
    THEN the returned list should contain the renamed extra artifacts.
    """
    inputs = [
        "scripts/script1.sh",
        "scripts/updater/updater.py",
    ]

    version_str = "v1.0.0"

    def rename(input):
        return ExtraArtifact._rename(input, version_str)

    outputs = [rename(i) for i in inputs]

    assert outputs == [
        "script1-v1.0.0.sh",
        "updater-v1.0.0.py",
    ]
