import os

import pytest
from click.testing import CliRunner

from east.__main__ import cli

from . import helpers
from .helpers import helper_test_against_west_run


def test_build_type_with_no_east_yml(west_workplace_parametrized, monkeypatch):
    """--build-type option can not be used if east.yml is not found in the project root.
    East needs to exit with error and message.
    """
    os.remove("east.yml")

    monkeypatch.chdir(west_workplace_parametrized["app"])
    runner = CliRunner()

    east_cmd = "build --build-type debug".split(" ")

    # Call from the project root
    result = runner.invoke(cli, east_cmd)
    assert result.exit_code == 1


# if in project but not in app or samples then --build-type should not be given,
# we are assuming that user might be trying to run build on tests or zephyr's samples or
# something else
def test_build_type_outside_project_dir(west_workplace, monkeypatch):
    """No --build-type should be given if east is called:
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
        ("", '-DCONF_FILE=conf/common.conf -DEAST_BUILD_TYPE="release"'),
        (
            "--build-type debug",
            '-DCONF_FILE=conf/common.conf -DOVERLAY_CONFIG="conf/debug.conf" -DEAST_BUILD_TYPE="debug"',
        ),
        (
            "--build-type uart",
            '-DCONF_FILE=conf/common.conf -DOVERLAY_CONFIG="conf/debug.conf;conf/uart.conf" -DEAST_BUILD_TYPE="uart"',
        ),
    ],
)
def test_build_type_single_app_behaviour(
    west_workplace, monkeypatch, mocker, build_type_flag, cmake_arg
):
    """Build command needs to parse the --build-type flag into appopriate command line
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
        ("test_one", "", '-DCONF_FILE=conf/common.conf -DEAST_BUILD_TYPE="release"'),
        (
            "test_one",
            "--build-type debug",
            (
                '-DCONF_FILE=conf/common.conf -DOVERLAY_CONFIG="conf/debug.conf"'
                ' -DEAST_BUILD_TYPE="debug"'
            ),
        ),
        (
            "test_one",
            "--build-type uart",
            (
                "-DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/debug.conf;conf/uart.conf"'
                ' -DEAST_BUILD_TYPE="uart"'
            ),
        ),
        ("test_two", "", '-DCONF_FILE=conf/common.conf -DEAST_BUILD_TYPE="release"'),
        (
            "test_two",
            "--build-type rtt",
            (
                '-DCONF_FILE=conf/common.conf -DOVERLAY_CONFIG="conf/rtt.conf"'
                ' -DEAST_BUILD_TYPE="rtt"'
            ),
        ),
        (
            "test_two",
            "--build-type debug-rtt",
            (
                "-DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/debug.conf;conf/rtt.conf"'
                ' -DEAST_BUILD_TYPE="debug-rtt"'
            ),
        ),
    ],
)
def test_build_type_multi_app_behaviour(
    west_workplace_multi_app, monkeypatch, mocker, multiapp, build_type_flag, cmake_arg
):
    """Build command needs to parse the --build-type flag into appopriate command line
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


def create_last_build_type_file(app_path, build_type, build_dir="build"):
    """Create last_build_type_file file inside build folder."""
    build_type_str = build_type.split(" ")[-1]
    if build_type_str == "":
        build_type_str = "release"

    helpers.create_and_write(
        app_path, f"{build_dir}/last_build_type_flag", build_type_str
    )


@pytest.mark.parametrize(
    "build_type_flag",
    [
        "",
        "--build-type debug",
        "--build-type uart",
    ],
)
def test_build_type_build_folder_behaviour_same_flags(
    west_workplace_parametrized, monkeypatch, mocker, build_type_flag
):
    """If the build folder with same conf files with that --build-type expects exits then
    no cmake args are added to the build command to avoid cmake rebuilds.
    """
    app_path = west_workplace_parametrized["app"]
    create_last_build_type_file(app_path, build_type_flag)

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
    """If the build folder exists but it has build flags that are not expected by the east
    then rebuild is triggered.
    """
    app_path = west_workplace_parametrized["app"]

    create_last_build_type_file(app_path, "--build-type release")

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        app_path,
        f"build {build_type_flag}",
        expected_west_cmd=(
            "build -- -DCONF_FILE=conf/common.conf"
            f' -DOVERLAY_CONFIG="{overlay_configs}" '
            f'-DEAST_BUILD_TYPE="{build_type_flag.split(" ")[1]}"'
        ),
    )


def test_build_type_non_existant_type(west_workplace_parametrized, monkeypatch, mocker):
    """If given --build-type does not exists then east needs to exit and throw message."""
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
    """Running east build with --build-type inside samples should fail."""
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
    """Test inherit key normal use."""
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
    """In case where sample (with an inherit keword) has a existing build folder from
    before, no extra cmake args should be emmited.
    """
    project_path = west_workplace_parametrized["project"]

    sample_path = os.path.join(project_path, "samples", "settings")

    create_last_build_type_file(sample_path, "--build-type debug")

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
    """In case where there is no inherit we default to basic west behavior: no cmake args."""
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
    """In case where sample does not exist in east.yml we default to basic west behaviour:
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
    """In case where sample is inheriting from a non-existing app we exit."""
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


east_yaml_inheriting_from_release_single_app = """
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
        build-type: release
"""

east_yaml_inheriting_from_release_multi_app = """
apps:
  - name: test_one
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf

  - name: test_two
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
        build-type: release
"""


def test_inheriting_from_release_build_type(
    west_workplace_parametrized, monkeypatch, mocker
):
    """It should be possible for a sample to inherit from a "release" build type. In that
    case only common.conf should be added to the build.
    """
    project_path = west_workplace_parametrized["project"]

    def west_cmd_fmt(prefix):
        return f"build -- -DCONF_FILE={prefix}conf/common.conf"

    if west_workplace_parametrized["project_type"] == "single":
        east_yml = east_yaml_inheriting_from_release_single_app

    if west_workplace_parametrized["project_type"] == "multi":
        east_yml = east_yaml_inheriting_from_release_multi_app

    helpers.create_and_write(
        project_path,
        "east.yml",
        east_yml,
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
    """In case where east.yml has duplicated app names exit and throw error."""
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
                ' -DEAST_BUILD_TYPE="release"'
            ),
        ),
        (
            "build -b nrf52840dk_nrf52840 --build-type uart",
            (
                "build -b nrf52840dk_nrf52840 -- -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf;'
                'conf/debug.conf;conf/uart.conf"'
                ' -DEAST_BUILD_TYPE="uart"'
            ),
        ),
        (
            "build -b nrf52840dk_nrf52840@1.0.0",
            (
                "build -b nrf52840dk_nrf52840@1.0.0 -- -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf"'
                ' -DEAST_BUILD_TYPE="release"'
            ),
        ),
        (
            "build -b nrf52840dk_nrf52840@1.0.0 --build-type uart",
            (
                "build -b nrf52840dk_nrf52840@1.0.0 -- -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf;'
                'conf/debug.conf;conf/uart.conf"'
                ' -DEAST_BUILD_TYPE="uart"'
            ),
        ),
        (
            "build -b nonexisting_board",
            "build -b nonexisting_board -- -DCONF_FILE=conf/common.conf"
            ' -DEAST_BUILD_TYPE="release"',
        ),
        (
            "build -b nonexisting_board --build-type debug",
            (
                "build -b nonexisting_board -- -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/debug.conf"'
                ' -DEAST_BUILD_TYPE="debug"'
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
    """In case where we are building for a specific board, build command needs to check in
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
    should just include the -d option and common.conf.
    """
    project_path = west_workplace_parametrized["app"]

    build_dir = "../different_build_dir"

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project_path,
        f"build -d {build_dir}",
        f"build -d {build_dir} -- -DCONF_FILE=conf/common.conf "
        '-DEAST_BUILD_TYPE="release"',
        should_succed=True,
    )


def test_different_build_dir_path_full_dir_same_build_type(
    west_workplace_parametrized, monkeypatch, mocker
):
    """With different build dir path and build folder that has same previous build type
    files as current ones the west command should just include -d option,
    and nothing else.
    """
    project_path = west_workplace_parametrized["app"]

    build_dir = "../different_build_dir"
    build_type = "--build-type uart"

    create_last_build_type_file(project_path, build_type, build_dir=build_dir)

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project_path,
        f"build -d {build_dir} {build_type}",
        f"build -d {build_dir}",
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

    old_build_type = "--build-type uart"
    new_build_type = "--build-type debug"
    new_overlay_configs = "conf/debug.conf"

    create_last_build_type_file(
        project_path, build_type=old_build_type, build_dir=build_dir
    )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project_path,
        f"build -d {build_dir} {new_build_type}",
        f"build -d {build_dir} -- -DCONF_FILE=conf/common.conf"
        f' -DOVERLAY_CONFIG="{new_overlay_configs}" -DEAST_BUILD_TYPE="debug"',
        should_succed=True,
    )


@pytest.mark.parametrize(
    "east_cmd, expected_west_cmd",
    [
        (
            "build app/test_one",
            (
                "build app/test_one -- -DCONF_FILE=conf/common.conf "
                '-DEAST_BUILD_TYPE="release"'
            ),
        ),
        (
            "build app/test_two",
            (
                "build app/test_two -- -DCONF_FILE=conf/common.conf "
                '-DEAST_BUILD_TYPE="release"'
            ),
        ),
        (
            "build app/test_one --build-type debug",
            (
                "build app/test_one -- -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/debug.conf"'
                ' -DEAST_BUILD_TYPE="debug"'
            ),
        ),
        (
            "build app/test_two --build-type debug",
            (
                "build app/test_two -- -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/debug.conf"'
                ' -DEAST_BUILD_TYPE="debug"'
            ),
        ),
        (
            "build -b nrf52840dk_nrf52840 app/test_one",
            (
                "build -b nrf52840dk_nrf52840 app/test_one --"
                " -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf"'
                ' -DEAST_BUILD_TYPE="release"'
            ),
        ),
        (
            "build -b nrf52840dk_nrf52840 --build-type uart app/test_one",
            (
                "build -b nrf52840dk_nrf52840 app/test_one --"
                " -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf;'
                'conf/debug.conf;conf/uart.conf"'
                ' -DEAST_BUILD_TYPE="uart"'
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
    """Using a different source dir must not affect the extra args after `--`."""
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
    """Test if sample with inherit key and source_dir works."""
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
        "build samples/settings",
        expected_west_cmd=west_cmd_fmt(west_workplace_parametrized["prefix"]),
        should_succed=True,
    )


def test_sample_with_inherit_and_with_source_dir_and_board(
    west_workplace_parametrized, monkeypatch, mocker
):
    """Test if sample with inherit key and source_dir works, when there is board involved."""
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
        "build -b nrf52840dk_nrf52840 samples/settings",
        expected_west_cmd=west_cmd_fmt(west_workplace_parametrized["prefix"]),
        should_succed=True,
    )


east_yaml_no_apps_key = """
samples:
  - name: settings
    west-boards:
      - custom_nrf52840dk
"""


def test_no_apps_key_in_east_yml_build_type(
    west_workplace_parametrized, monkeypatch, mocker
):
    """Apps key is optional.
    Running east build with no apps key in east.yml should fail if --build-type is
    given.
    """
    helpers.create_and_write(
        west_workplace_parametrized["project"],
        "east.yml",
        east_yaml_no_apps_key,
    )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        west_workplace_parametrized["app"],
        "build --build-type debug",
        should_succed=False,
    )


def test_no_apps_key_in_east_yml_app(west_workplace_parametrized, monkeypatch, mocker):
    """Apps key is optional.
    Running east build with no apps key in east.yml and building for app should not emit
    any extra cmake args.
    """
    helpers.create_and_write(
        west_workplace_parametrized["project"],
        "east.yml",
        east_yaml_no_apps_key,
    )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        west_workplace_parametrized["app"],
        "build",
        "build",
    )


def test_no_apps_key_in_east_yml_sample(
    west_workplace_parametrized, monkeypatch, mocker
):
    """Apps key is optional.
    Running east build with no apps key in east.yml should not emit any extra cmake
    args.
    """
    helpers.create_and_write(
        west_workplace_parametrized["project"],
        "east.yml",
        east_yaml_no_apps_key,
    )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        os.path.join(west_workplace_parametrized["project"], "samples", "settings"),
        "build",
        "build",
        should_succed=True,
    )


east_yaml_no_samples_key = """
apps:
  - name: test_one
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf
"""


def test_no_samples_key_in_east_yml(west_workplace_parametrized, monkeypatch, mocker):
    """Samples key is optional.
    Running east build with no samples key in east.yml in samples should not emit any
    extra args.
    """
    helpers.create_and_write(
        west_workplace_parametrized["project"],
        "east.yml",
        east_yaml_no_samples_key,
    )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        os.path.join(west_workplace_parametrized["project"], "samples", "settings"),
        "build",
        "build",
        should_succed=True,
    )


east_yaml_empty_apps_key = """
apps:
"""


def test_empty_apps_key(west_workplace_parametrized, monkeypatch, mocker):
    """Empty apps key is not allowed."""
    helpers.create_and_write(
        west_workplace_parametrized["project"],
        "east.yml",
        east_yaml_empty_apps_key,
    )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        west_workplace_parametrized["app"],
        "build",
        should_succed=False,
    )


@pytest.mark.parametrize(
    "build_path",
    [
        "project",
        "test",
    ],
)
def test_building_outside_of_app_and_samples(
    west_workplace_parametrized, build_path, monkeypatch, mocker
):
    """Empty apps key is not allowed, and samples can not inherit from it."""
    helper_test_against_west_run(
        monkeypatch,
        mocker,
        west_workplace_parametrized[build_path],
        "build -b native_posix",
        "build -b native_posix",
        should_succed=True,
    )


def test_building_app_that_is_not_in_east_yaml(
    west_workplace_parametrized, monkeypatch, mocker
):
    """East shouldn't add extra flags to the west build call when building an app that
    isn't in the east.yaml.
    """
    unlisted_app = os.path.join(
        west_workplace_parametrized["project"], "app/test_three"
    )
    os.makedirs(unlisted_app, exist_ok=True)

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        west_workplace_parametrized["project"],
        "build -b native_posix app/test_three",
        "build -b native_posix app/test_three",
        should_succed=True,
    )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        unlisted_app,
        "build -b native_posix",
        "build -b native_posix",
        should_succed=True,
    )


def test_empty_east_yml_is_valid(west_workplace_parametrized, monkeypatch, mocker):
    """Apps and sample keys are both optional in east.yaml, so empty east.yml is valid."""
    # Create empty east.yml
    open(os.path.join(west_workplace_parametrized["project"], "east.yml"), "w").close()

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        west_workplace_parametrized["app"],
        "build -b native_posix",
        "build -b native_posix",
        should_succed=True,
    )


east_yaml_no_build_type = """
apps:
  - name: test_one
    west-boards:
      - custom_nrf52840dk
"""


def test_no_build_type_is_ok(west_workplace_parametrized, monkeypatch, mocker):
    """East should not add any extra flags to the west build call when no build type is
    specified in the east.yaml.
    """
    project = west_workplace_parametrized["project"]
    helpers.create_and_write(
        project,
        "east.yml",
        east_yaml_no_build_type,
    )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        west_workplace_parametrized["app"],
        "build -b custom_nrf52840dk",
        expected_west_cmd="build -b custom_nrf52840dk",
    )


def test_build_type_as_arg_is_not_ok_if_not_in_east_yml(
    west_workplace_parametrized, monkeypatch, mocker
):
    """East should abort if build type is given as an argument but built-types key is
    not present in the east.yaml.
    """
    project = west_workplace_parametrized["project"]
    helpers.create_and_write(
        project,
        "east.yml",
        east_yaml_no_build_type,
    )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        west_workplace_parametrized["app"],
        "build -b custom_nrf52840dk --build-type debug",
        should_succed=False,
    )


east_yaml_no_build_type_inheriting = """
apps:
  - name: test_one
    west-boards:
      - custom_nrf52840dk

samples:
  - name: settings
    west-boards:
      - custom_nrf52840dk
    inherit-build-type:
        app: test_one
        build-type: debug
"""


def test_inheriting_from_an_app_without_build_type_should_fail(
    west_workplace_parametrized, monkeypatch, mocker
):
    """Test that inheriting from an app without build type fails."""
    project = west_workplace_parametrized["project"]
    helpers.create_and_write(
        project,
        "east.yml",
        east_yaml_no_build_type_inheriting,
    )

    sample_path = os.path.join(project, "samples", "settings")

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        sample_path,
        "build -b custom_nrf52840dk",
        should_succed=False,
    )


@pytest.mark.parametrize(
    "east_cmd, expected_west_cmd",
    [
        (
            "build --snippet rtt app/test_one",
            (
                "build --snippet rtt app/test_one -- -DCONF_FILE=conf/common.conf "
                '-DEAST_BUILD_TYPE="release"'
            ),
        ),
        (
            "build --snippet rtt app/test_two",
            (
                "build --snippet rtt app/test_two -- -DCONF_FILE=conf/common.conf "
                '-DEAST_BUILD_TYPE="release"'
            ),
        ),
        (
            "build --snippet rtt app/test_one --build-type debug",
            (
                "build --snippet rtt app/test_one -- -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/debug.conf"'
                ' -DEAST_BUILD_TYPE="debug"'
            ),
        ),
        (
            "build --snippet rtt app/test_two --build-type debug",
            (
                "build --snippet rtt app/test_two -- -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/debug.conf"'
                ' -DEAST_BUILD_TYPE="debug"'
            ),
        ),
        (
            "build -b nrf52840dk_nrf52840 --snippet rtt app/test_one",
            (
                "build -b nrf52840dk_nrf52840 --snippet rtt app/test_one --"
                " -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf"'
                ' -DEAST_BUILD_TYPE="release"'
            ),
        ),
        (
            "build --snippet rtt -b nrf52840dk_nrf52840 --build-type uart app/test_one",
            (
                "build --snippet rtt -b nrf52840dk_nrf52840 app/test_one --"
                " -DCONF_FILE=conf/common.conf"
                ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf;'
                'conf/debug.conf;conf/uart.conf"'
                ' -DEAST_BUILD_TYPE="uart"'
            ),
        ),
    ],
)
def test_additional_flags_should_passthrough(
    west_workplace_multi_app, monkeypatch, mocker, east_cmd, expected_west_cmd
):
    """Test that additional flags, such as --snippet, pass through east logic unchanged."""
    project = west_workplace_multi_app

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project,
        east_cmd,
        expected_west_cmd,
    )
