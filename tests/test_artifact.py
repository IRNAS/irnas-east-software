from east.modules.artifact import Artifact


def test_renaming_artefacts_from_project_using_sysbuild():
    """Test renaming artifacts from a project using sysbuild.

    GIVEN a list of artifacts from a project using sysbuild,
    WHEN renaming artifacts,
    THEN the returned list should contain the renamed artifacts.
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
        return Artifact._rename(input, project_name, app_build_dir, version_str)

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


def test_renaming_artefacts_from_project_not_using_sysbuild():
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
        return Artifact._rename(input, project_name, app_build_dir, version_str)

    outputs = [rename(i) for i in inputs]

    assert outputs == [
        "blinky.prod-zephyr-v1.0.0.hex",
        "blinky.prod-Kconfig-Kconfig-v1.0.0.dts",
        "blinky.prod-dfu_application-v1.0.0.zip",
        "blinky.prod-merged-v1.0.0.hex",
        "blinky.prod-zephyr.arch-cmake_install-v1.0.0.cmake",
    ]
