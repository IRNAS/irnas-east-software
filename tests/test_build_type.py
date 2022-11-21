import os

import pytest
from click.testing import CliRunner

import east
from east.__main__ import cli

from . import helpers


def helper_test_against_west_run(
    monkeypatch, mocker, path, east_cmd, expected_west_cmd=None, should_succed=True
):
    """
    Helper function for making tests easier to read.

    Args:
        monkeypatch ():         fixture
        mocker ():              fixture
        path ():                To which path should we change
        east_cmd ():            which east command should be called
        expected_west_cmd ():   what is expected west cmd that should be produced. If
                                none then no run_west call should happend.
        should_succed ():       If true then the command should succeded.

    Returns:
        Result object, which can be further checked.
    """
    runner = CliRunner()

    monkeypatch.chdir(path)
    mocker.patch("east.east_context.EastContext.run_west")

    # Setting catch_exceptions to False enables us to see programming errors in East
    # code
    result = runner.invoke(cli, east_cmd.strip().split(" "), catch_exceptions=False)

    run_west = east.east_context.EastContext.run_west

    if expected_west_cmd:
        run_west.assert_called_once_with(expected_west_cmd)
    else:
        run_west.assert_not_called()

    if should_succed:
        expected_return_code = 0
    else:
        expected_return_code = 1

    assert result.exit_code == expected_return_code
    return result


def helper_test_against_west_run1(
    monkeypatch, mocker, path, east_cmd, expected_west_cmd=None, should_succed=True
):
    """
    Helper function for making tests easier to read.

    Args:
        monkeypatch ():         fixture
        mocker ():              fixture
        path ():                To which path should we change
        east_cmd ():            which east command should be called
        expected_west_cmd ():   what is expected west cmd that should be produced. If
                                none then no run_west call should happend.
        should_succed ():       If true then the command should succeded.

    Returns:
        Result object, which can be further checked.
    """
    runner = CliRunner()

    monkeypatch.chdir(path)
    mocker.patch("east.east_context.EastContext.run_west")

    result = runner.invoke(cli, east_cmd.strip().split(" "))
    print(result.output)


# if in project but not in app or samples then --build-type should not be given,
# we are assuming that user might be trying to run build on tests or zephyr's samples or
# something else
def test_build_type_outside_project_dir(west_workplace, monkeypatch):
    """
    No --build-type should be given if east is called:
    - inside of project dir, but not in app
    - outside of project dir
    East needs to exit with error and message.
    """

    project_path = west_workplace
    runner = CliRunner()

    east_cmd = "build --build-type debug".split(" ")

    # Call from the project root
    result = runner.invoke(cli, east_cmd)
    assert result.exit_code == 1

    # Go one level up from project dir
    monkeypatch.chdir(os.path.dirname(project_path))
    result = runner.invoke(cli, east_cmd)
    assert result.exit_code == 1

    # Go into zephyr folder
    monkeypatch.chdir(os.path.join(os.path.dirname(project_path), "zephyr"))
    result = runner.invoke(cli, east_cmd)
    assert result.exit_code == 1


# in single app folder behaviour
@pytest.mark.parametrize(
    "build_type_flag, cmake_arg",
    [
        ("", "-DCONF_FILE=conf/common.conf"),
        (
            "--build-type debug",
            '-DCONF_FILE=conf/common.conf -DOVERLAY_CONFIG="conf/debug.conf"',
        ),
        (
            "--build-type uart",
            (
                "-DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/debug.conf;conf/uart.conf"'
            ),
        ),
    ],
)
def test_build_type_single_app_behaviour(
    west_workplace, monkeypatch, mocker, build_type_flag, cmake_arg
):
    """
    build command needs to parse the --build-type flag into appopriate command line
    arguments.

    This test case is for a single app behaviour.
    """
    project_path = west_workplace
    helper_test_against_west_run(
        monkeypatch,
        mocker,
        os.path.join(project_path, "app"),
        f"build {build_type_flag}",
        expected_west_cmd=f"build -- {cmake_arg}",
    )


@pytest.mark.parametrize(
    "multiapp, build_type_flag, cmake_arg",
    [
        ("test_one", "", "-DCONF_FILE=conf/common.conf"),
        (
            "test_one",
            "--build-type debug",
            '-DCONF_FILE=conf/common.conf -DOVERLAY_CONFIG="conf/debug.conf"',
        ),
        (
            "test_one",
            "--build-type uart",
            (
                "-DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/debug.conf;conf/uart.conf"'
            ),
        ),
        ("test_two", "", "-DCONF_FILE=conf/common.conf"),
        (
            "test_two",
            "--build-type rtt",
            '-DCONF_FILE=conf/common.conf -DOVERLAY_CONFIG="conf/rtt.conf"',
        ),
        (
            "test_two",
            "--build-type debug-rtt",
            (
                "-DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/debug.conf;conf/rtt.conf"'
            ),
        ),
    ],
)
def test_build_type_multi_app_behaviour(
    west_workplace_multi_app, monkeypatch, mocker, multiapp, build_type_flag, cmake_arg
):
    """
    build command needs to parse the --build-type flag into appopriate command line
    arguments.

    This test case is for a multi app behaviour.
    """
    project_path = west_workplace_multi_app

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        os.path.join(project_path, "app", multiapp),
        f"build {build_type_flag}",
        expected_west_cmd=f"build -- {cmake_arg}",
    )


def create_image_preload_file(
    app_path, path_prefix="", overlay_configs=None, build_dir="build"
):
    """create image_preload.cmake file inside build folder."""

    image_preload_file = (
        "# Generated file that can be used to preload variant"
        f' images\nset(CACHED_CONF_FILE "{path_prefix}conf/common.conf" CACHE INTERNAL'
        ' "NCS child image controlled")\nset(DTC_OVERLAY_FILE "" CACHE INTERNAL "NCS'
        ' child image controlled")\nset(WEST_PYTHON "/usr/bin/python3" CACHE INTERNAL'
        ' "NCS child image controlled")\n'
    )

    if overlay_configs:
        image_preload_file += (
            f'set(OVERLAY_CONFIG "{path_prefix}{overlay_configs}" CACHE INTERNAL "NCS'
            ' child image controlled")\n'
        )

    helpers.create_and_write(
        app_path, f"{build_dir}/image_preload.cmake", image_preload_file
    )


@pytest.mark.parametrize(
    "build_type_flag, overlay_configs",
    [
        ("", None),
        (
            "--build-type debug",
            "conf/debug.conf",
        ),
        (
            "--build-type uart",
            "conf/debug.conf;conf/uart.conf",
        ),
    ],
)
def test_build_type_build_folder_behaviour_same_flags(
    west_workplace_parametrized, monkeypatch, mocker, build_type_flag, overlay_configs
):
    """
    If the build folder with same conf files with that --build-type expects exits then
    no cmake args are added to the build command to avoid cmake rebuilds.
    """
    app_path = west_workplace_parametrized["app"]
    create_image_preload_file(app_path, overlay_configs=overlay_configs)

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        app_path,
        f"build {build_type_flag}",
        expected_west_cmd="build",
    )


@pytest.mark.parametrize(
    "build_type_flag, overlay_configs",
    [
        (
            "--build-type debug",
            "conf/debug.conf",
        ),
        (
            "--build-type uart",
            "conf/debug.conf;conf/uart.conf",
        ),
    ],
)
def test_build_type_build_folder_behaviour_different_flags(
    west_workplace_parametrized, monkeypatch, mocker, build_type_flag, overlay_configs
):
    """
    If the build folder exsits but it has build flags that are not expected by the east
    then rebuild is triggered.
    """
    app_path = west_workplace_parametrized["app"]
    create_image_preload_file(app_path)

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        app_path,
        f"build {build_type_flag}",
        expected_west_cmd=(
            "build -- -DCONF_FILE=conf/common.conf"
            f' -DOVERLAY_CONFIG="{overlay_configs}"'
        ),
    )


def test_build_type_non_existant_type(west_workplace_parametrized, monkeypatch, mocker):
    """
    If given --build-type does not exists then east needs to exit and throw message.
    """
    app_path = west_workplace_parametrized["app"]

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        app_path,
        "build --build-type asasdada",
        should_succed=False,
    )


def test_build_type_samples_with_build_type_option(
    west_workplace_parametrized, monkeypatch, mocker
):
    """
    Running east build with --build-type inside samples should fail.
    """
    project_path = west_workplace_parametrized["project"]
    sample_path = os.path.join(project_path, "samples", "settings")

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        sample_path,
        "build --build-type debug",
        should_succed=False,
    )


def test_build_type_samples_inherit(west_workplace_parametrized, monkeypatch, mocker):
    """
    Test inherit key normal use.
    """

    project_path = west_workplace_parametrized["project"]

    def west_cmd_fmt(prefix):
        return (
            f"build -- -DCONF_FILE={prefix}conf/common.conf"
            f' -DOVERLAY_CONFIG="{prefix}conf/debug.conf"'
        )

    sample_path = os.path.join(project_path, "samples", "settings")
    helper_test_against_west_run(
        monkeypatch,
        mocker,
        sample_path,
        "build",
        expected_west_cmd=west_cmd_fmt(west_workplace_parametrized["prefix"]),
        should_succed=True,
    )


def test_build_type_samples_inherit_build_folder_same_flag(
    west_workplace_parametrized, monkeypatch, mocker
):
    """
    In case where sample (with an inherit keword) has a existing build folder from
    before, no extra cmake args should be emmited.
    """
    project_path = west_workplace_parametrized["project"]

    sample_path = os.path.join(project_path, "samples", "settings")

    overlay_configs = "conf/debug.conf"
    create_image_preload_file(
        sample_path,
        path_prefix=west_workplace_parametrized["prefix"],
        overlay_configs=overlay_configs,
    )
    helper_test_against_west_run(
        monkeypatch,
        mocker,
        sample_path,
        "build",
        expected_west_cmd="build",
        should_succed=True,
    )


def test_build_type_samples_no_inherit(
    west_workplace_parametrized, monkeypatch, mocker
):
    """
    In case where there is no inherit we default to basic west behavior: no cmake args.
    """

    project_path = west_workplace_parametrized["project"]
    sample_path = os.path.join(project_path, "samples", "dfu")

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        sample_path,
        "build",
        expected_west_cmd="build",
        should_succed=True,
    )


def test_build_type_samples_does_not_exist(
    west_workplace_parametrized, monkeypatch, mocker
):
    """
    In case where sample does not exist in east.yml we default to basic west behaviour:
    no cmake args.

    """
    project_path = west_workplace_parametrized["project"]

    sample_path = os.path.join(project_path, "samples", "super_duper_sample")
    os.mkdir(sample_path)

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        sample_path,
        "build",
        expected_west_cmd="build",
        should_succed=True,
    )


east_yaml_non_existing_inheriting = """
apps:
  - name: test_one
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf

samples:
  - name: settings
    west-boards:
      - custom_nrf52840dk
    inherit-build-type:
        app: test_two
        build-type: debug
"""


def test_non_existing_inherited_app(west_workplace_parametrized, monkeypatch, mocker):
    """
    In case where sample is inheriting from a non-existing app we exit.

    """

    project_path = west_workplace_parametrized["project"]

    helpers.create_and_write(
        project_path,
        "east.yml",
        east_yaml_non_existing_inheriting,
    )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project_path,
        "build",
        should_succed=False,
    )


east_yaml_duplicated_app_names = """
apps:
  - name: test_one
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf

  - name: test_one
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf

samples:
  - name: settings
    west-boards:
      - custom_nrf52840dk
    inherit-build-type:
        app: test_one
        build-type: debug

  - name: dfu
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840
    # Don't inherit, use prj.conf in the sample's folder.
"""

east_yaml_duplicated_samples_names = """
apps:
  - name: test_one
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf

samples:
  - name: settings
    west-boards:
      - custom_nrf52840dk
    inherit-build-type:
        app: test_one
        build-type: debug

  - name: settings
    west-boards:
      - custom_nrf52840dk

  - name: dfu
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840
    # Don't inherit, use prj.conf in the sample's folder.
"""

east_yaml_duplicated_build_types = """
apps:
  - name: test_one
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf
      - type: debug
        conf-files:
          - debug.conf
      - type: debug
        conf-files:
          - debug.conf
      - type: rtt
        conf-files:
          - debug.conf

samples:
  - name: settings
    west-boards:
      - custom_nrf52840dk
    inherit-build-type:
        app: test_one
        build-type: debug

  - name: dfu
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840
    # Don't inherit, use prj.conf in the sample's folder.
"""


@pytest.mark.parametrize(
    "east_yml",
    [
        "east_yaml_duplicated_app_names",
        "east_yaml_duplicated_build_types",
        "east_yaml_duplicated_samples_names",
    ],
)
def test_duplicated_names_in_east_yml(
    west_workplace_multi_app, monkeypatch, mocker, east_yml
):
    """
    In case where east.yml has duplicated app names exit and throw error.
    """

    helpers.create_and_write(
        west_workplace_multi_app,
        "east.yml",
        east_yml,
    )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        west_workplace_multi_app,
        "build",
        should_succed=False,
    )


@pytest.mark.parametrize(
    "east_cmd, expected_west_cmd",
    [
        (
            "build -b nrf52840dk_nrf52840",
            (
                "build -b nrf52840dk_nrf52840 -- -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf"'
            ),
        ),
        (
            "build -b nrf52840dk_nrf52840 --build-type uart",
            (
                "build -b nrf52840dk_nrf52840 -- -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf;'
                'conf/debug.conf;conf/uart.conf"'
            ),
        ),
        (
            "build -b nrf52840dk_nrf52840@1.0.0",
            (
                "build -b nrf52840dk_nrf52840@1.0.0 -- -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf"'
            ),
        ),
        (
            "build -b nrf52840dk_nrf52840@1.0.0 --build-type uart",
            (
                "build -b nrf52840dk_nrf52840@1.0.0 -- -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf;'
                'conf/debug.conf;conf/uart.conf"'
            ),
        ),
        (
            "build -b nonexisting_board",
            "build -b nonexisting_board -- -DCONF_FILE=conf/common.conf",
        ),
        (
            "build -b nonexisting_board --build-type debug",
            (
                "build -b nonexisting_board -- -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/debug.conf"'
            ),
        ),
    ],
)
def test_searching_for_west_board_specific_confs(
    west_workplace_parametrized,
    monkeypatch,
    mocker,
    east_cmd,
    expected_west_cmd,
):
    """
    In case where we are building for a specific board, build command needs to check in
    the conf folder if a file with name west_board.conf exists, if yes then it needs to
    add it.
    In sample folders with inherit key it needs to do the same thing.
    """
    project_path = west_workplace_parametrized["app"]

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project_path,
        east_cmd,
        expected_west_cmd,
        should_succed=True,
    )


def test_different_build_dir_path_empty_dir(
    west_workplace_parametrized, monkeypatch, mocker
):
    """With different build dir path, but no build folder the expected west command
    should just include the -d option and common.conf"""

    project_path = west_workplace_parametrized["app"]

    build_dir = "../different_build_dir"

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project_path,
        f"build -d {build_dir}",
        f"build -d {build_dir} -- -DCONF_FILE=conf/common.conf",
        should_succed=True,
    )


def test_different_build_dir_path_full_dir_same_build_type(
    west_workplace_parametrized, monkeypatch, mocker
):
    """With different build dir path and build folder that has same previous build type
    files as current ones the west command should just include -d option and nothing
    else.
    """

    project_path = west_workplace_parametrized["app"]

    build_dir = "../different_build_dir"

    # Config for uart build type
    overlay_configs = "conf/debug.conf;conf/uart.conf"

    create_image_preload_file(
        os.path.join(project_path, build_dir),
        path_prefix=west_workplace_parametrized["prefix"],
        overlay_configs=overlay_configs,
    )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project_path,
        f"build -d {build_dir} --build-type uart",
        f"build -d {build_dir} -- -DCONF_FILE=conf/common.conf"
        f' -DOVERLAY_CONFIG="{overlay_configs}"',
        should_succed=True,
    )


def test_different_build_dir_path_full_dir_different_build_type(
    west_workplace_parametrized, monkeypatch, mocker
):
    """With different build dir path and build folder that has different previous build
    type files as current ones the west command should include -d option and current
    conf files.
    """

    project_path = west_workplace_parametrized["app"]

    build_dir = "../different_build_dir"

    # Config for uart build type
    old_overlay_configs = "conf/debug.conf;conf/uart.conf"
    # Config for debug build type
    new_overlay_configs = "conf/debug.conf"

    create_image_preload_file(
        os.path.join(project_path, build_dir),
        path_prefix=west_workplace_parametrized["prefix"],
        overlay_configs=old_overlay_configs,
    )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project_path,
        f"build -d {build_dir} --build-type debug",
        f"build -d {build_dir} -- -DCONF_FILE=conf/common.conf"
        f' -DOVERLAY_CONFIG="{new_overlay_configs}"',
        should_succed=True,
    )


# @pytest.mark.parametrize("app_path", [, "app/test_two"])
@pytest.mark.parametrize(
    "east_cmd, expected_west_cmd",
    [
        (
            "build -s app/test_one",
            "build app/test_one -- -DCONF_FILE=conf/common.conf",
        ),
        (
            "build -s app/test_two",
            "build app/test_two -- -DCONF_FILE=conf/common.conf",
        ),
        (
            "build -s app/test_one --build-type debug",
            (
                "build app/test_one -- -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/debug.conf"'
            ),
        ),
        (
            "build -s app/test_two --build-type debug",
            (
                "build app/test_two -- -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/debug.conf"'
            ),
        ),
        (
            "build -s app/test_one -b nrf52840dk_nrf52840",
            (
                "build -b nrf52840dk_nrf52840 app/test_one --"
                " -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf"'
            ),
        ),
        (
            "build -s app/test_one -b nrf52840dk_nrf52840 --build-type uart",
            (
                "build -b nrf52840dk_nrf52840 app/test_one --"
                " -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf;'
                'conf/debug.conf;conf/uart.conf"'
            ),
        ),
    ],
)
def test_using_different_source_dirs(
    west_workplace_multi_app,
    monkeypatch,
    mocker,
    east_cmd,
    expected_west_cmd,
):
    """
    Using a different source dir must not affect the extra args after `--`.
    """
    project_path = west_workplace_multi_app

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project_path,
        east_cmd,
        expected_west_cmd,
        should_succed=True,
    )


def test_sample_with_inherit_and_with_source_dir(
    west_workplace_parametrized, monkeypatch, mocker
):
    """
    Test if sample with inherit key and source_dir works
    """

    project_path = west_workplace_parametrized["project"]

    def west_cmd_fmt(prefix):
        return (
            f"build samples/settings -- -DCONF_FILE={prefix}conf/common.conf"
            f' -DOVERLAY_CONFIG="{prefix}conf/debug.conf"'
        )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project_path,
        "build -s samples/settings",
        expected_west_cmd=west_cmd_fmt(west_workplace_parametrized["prefix"]),
        should_succed=True,
    )


def test_sample_with_inherit_and_with_source_dir_and_board(
    west_workplace_parametrized, monkeypatch, mocker
):
    """
    Test if sample with inherit key and source_dir works, when there is board involved.
    """

    project_path = west_workplace_parametrized["project"]

    def west_cmd_fmt(prefix):
        return (
            "build -b nrf52840dk_nrf52840 samples/settings --"
            f" -DCONF_FILE={prefix}conf/common.conf"
            " -DOVERLAY_CONFIG="
            f'"{prefix}conf/nrf52840dk_nrf52840.conf;{prefix}conf/debug.conf"'
        )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project_path,
        "build -s samples/settings -b nrf52840dk_nrf52840",
        expected_west_cmd=west_cmd_fmt(west_workplace_parametrized["prefix"]),
        should_succed=True,
    )
