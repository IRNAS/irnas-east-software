import os

from click.testing import CliRunner

import east
from east.__main__ import cli
from east.east_context import EastContext
from east.helper_functions import find_all_boards

from . import helpers
from .helpers import helper_test_against_west_run1


def helper_test_against_west_run(
    monkeypatch, mocker, path, east_cmd, expected_west_cmds=None, should_succed=True
):
    """
    Helper function for making tests easier to read.

    Args:
        monkeypatch ():         fixture
        mocker ():              fixture
        path ():                To which path should we change
        east_cmd ():            which east command should be called
        expected_west_cmds ():  List of expected west_cmds. If
                                none then no run_west call should happend.
        should_succed ():       If true then the command should succeded.

    Returns:
        Result object, which can be further checked.
    """
    runner = CliRunner()

    # Mock output of git commmand, so tests do not have to depend on it
    mocker.patch(
        "east.workspace_commands.release_commands.get_git_version",
        return_value={"tag": "v1.0.0.", "hash": ""},
    )

    monkeypatch.chdir(path)
    mocker.patch(
        "east.east_context.EastContext.run_west",
        return_value={"output": "", "returncode": 0},
    )

    # Setting catch_exceptions to False enables us to see programming errors in East
    # code
    result = runner.invoke(cli, east_cmd.strip().split(" "), catch_exceptions=False)

    run_west = east.east_context.EastContext.run_west

    if expected_west_cmds:
        # This conversion is needed due to assert_has_calls interface
        calls = [
            # mocker.call(cmd, silent=True, return_output=True, exit_on_error=False)
            mocker.call(cmd)
            for cmd in expected_west_cmds
        ]
        run_west.assert_has_calls(calls)
    else:
        run_west.assert_not_called()

    expected_return_code = 0 if should_succed else 1

    assert result.exit_code == expected_return_code
    return result


east_yaml_single_app = """
apps:
  - name: test_one
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf
      - type: uart
        conf-files:
          - debug.conf
          - uart.conf
"""


def test_finding_hardware_versions(west_workplace):
    _ = west_workplace
    east = EastContext()

    # Some board that has as several different versions in board folder
    boards = find_all_boards(east, "custom_nrf52840dk")
    expected_boards = [
        "custom_nrf52840dk@1.0.0",
        "custom_nrf52840dk@1.1.0",
        "custom_nrf52840dk@2.20.1",
    ]
    assert expected_boards == boards

    # Some board that has a board folder but not revisions
    boards = find_all_boards(east, "nrf52840dk_nrf52840")
    expected_boards = ["nrf52840dk_nrf52840"]
    assert expected_boards == boards

    # Non-existing in sense that it does not have its own boards folder.
    boards = find_all_boards(east, "non_existing_board")
    expected_boards = ["non_existing_board"]
    assert expected_boards == boards


def test_no_east_yml_with_release(west_workplace_parametrized, monkeypatch, mocker):
    """
    Running east release with not east.yml should abort.
    """

    os.remove("east.yml")

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        west_workplace_parametrized["project"],
        "release",
        should_succed=False,
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
      - type: uart
        conf-files:
          - debug.conf
          - uart.conf
"""

expected_app_release_west_commands = [
    (
        "build -b custom_nrf52840dk@1.0.0 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/debug.conf"'
    ),
    (
        "build -b custom_nrf52840dk@1.0.0 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/debug.conf;conf/uart.conf"'
    ),
    "build -b custom_nrf52840dk@1.0.0 app -- -DCONF_FILE=conf/common.conf",
    (
        "build -b custom_nrf52840dk@1.1.0 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/debug.conf"'
    ),
    (
        "build -b custom_nrf52840dk@1.1.0 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/debug.conf;conf/uart.conf"'
    ),
    "build -b custom_nrf52840dk@1.1.0 app -- -DCONF_FILE=conf/common.conf",
    (
        "build -b custom_nrf52840dk@2.20.1 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/debug.conf"'
    ),
    (
        "build -b custom_nrf52840dk@2.20.1 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/debug.conf;conf/uart.conf"'
    ),
    "build -b custom_nrf52840dk@2.20.1 app -- -DCONF_FILE=conf/common.conf",
    (
        "build -b nrf52840dk_nrf52840 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf;conf/debug.conf"'
    ),
    (
        "build -b nrf52840dk_nrf52840 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf;conf/debug.conf;conf/uart.conf"'
    ),
    (
        "build -b nrf52840dk_nrf52840 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf"'
    ),
]


def test_basic_app_release_behaviour(west_workplace, monkeypatch, mocker):
    """
    Running east release with samples key, should skip build process for samples and build
    apps.
    """

    project_path = west_workplace

    helpers.create_and_write(
        project_path,
        "east.yml",
        east_yaml_no_samples_key,
    )

    monkeypatch.setattr(east.workspace_commands.release_commands, "RUNNING_TESTS", True)

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project_path,
        "release",
        expected_west_cmds=expected_app_release_west_commands,
    )


east_yaml_no_apps_key = """
samples:
  - name: settings
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840

  - name: dfu
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840
"""

expected_samples_release_west_commands = [
    "build -b custom_nrf52840dk@1.0.0 samples/settings",
    "build -b custom_nrf52840dk@1.1.0 samples/settings",
    "build -b custom_nrf52840dk@2.20.1 samples/settings",
    "build -b nrf52840dk_nrf52840 samples/settings",
    "build -b custom_nrf52840dk@1.0.0 samples/dfu",
    "build -b custom_nrf52840dk@1.1.0 samples/dfu",
    "build -b custom_nrf52840dk@2.20.1 samples/dfu",
    "build -b nrf52840dk_nrf52840 samples/dfu",
]


def test_basic_samples_release_behaviour(
    west_workplace_parametrized, monkeypatch, mocker
):
    """
    Running east release with no apps key, should skip build process for apps and build
    samples.
    """

    helpers.create_and_write(
        west_workplace_parametrized["project"],
        "east.yml",
        east_yaml_no_apps_key,
    )

    monkeypatch.setattr(east.workspace_commands.release_commands, "RUNNING_TESTS", True)

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        west_workplace_parametrized["project"],
        "release",
        expected_west_cmds=expected_samples_release_west_commands,
    )


def test_basic_release_behaviour(west_workplace, monkeypatch, mocker):
    """
    Running east release with both apps and samples keys should run normally.
    """
    project_path = west_workplace

    helpers.create_and_write(
        project_path,
        "east.yml",
        east_yaml_no_apps_key + east_yaml_no_samples_key,
    )
    monkeypatch.setattr(east.workspace_commands.release_commands, "RUNNING_TESTS", True)

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project_path,
        "release",
        expected_west_cmds=expected_app_release_west_commands
        + expected_samples_release_west_commands,
    )
