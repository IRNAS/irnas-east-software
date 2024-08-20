import os
import shutil as sh

import east
from east.east_context import EastContext
from east.helper_functions import find_all_boards

from . import helpers
from .helpers import helper_test_against_west_run


def test_finding_hardware_versions(west_workplace):
    """Test finding hardware versions."""
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


def test_no_east_yml_with_release(west_workplace_parametrized, monkeypatch, mocker):
    """Running east release with not east.yml should abort."""
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
        ' -DEAST_BUILD_TYPE="debug"'
    ),
    (
        "build -b custom_nrf52840dk@1.0.0 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/debug.conf;conf/uart.conf"'
        ' -DEAST_BUILD_TYPE="uart"'
    ),
    (
        "build -b custom_nrf52840dk@1.0.0 app -- -DCONF_FILE=conf/common.conf"
        ' -DEAST_BUILD_TYPE="release"'
    ),
    (
        "build -b custom_nrf52840dk@1.1.0 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/debug.conf"'
        ' -DEAST_BUILD_TYPE="debug"'
    ),
    (
        "build -b custom_nrf52840dk@1.1.0 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/debug.conf;conf/uart.conf"'
        ' -DEAST_BUILD_TYPE="uart"'
    ),
    (
        "build -b custom_nrf52840dk@1.1.0 app -- -DCONF_FILE=conf/common.conf"
        ' -DEAST_BUILD_TYPE="release"'
    ),
    (
        "build -b custom_nrf52840dk@2.20.1 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/debug.conf"'
        ' -DEAST_BUILD_TYPE="debug"'
    ),
    (
        "build -b custom_nrf52840dk@2.20.1 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/debug.conf;conf/uart.conf"'
        ' -DEAST_BUILD_TYPE="uart"'
    ),
    (
        "build -b custom_nrf52840dk@2.20.1 app -- -DCONF_FILE=conf/common.conf"
        ' -DEAST_BUILD_TYPE="release"'
    ),
    (
        "build -b nrf52840dk_nrf52840 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf;conf/debug.conf"'
        ' -DEAST_BUILD_TYPE="debug"'
    ),
    (
        "build -b nrf52840dk_nrf52840 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf;conf/debug.conf;conf/uart.conf"'
        ' -DEAST_BUILD_TYPE="uart"'
    ),
    (
        "build -b nrf52840dk_nrf52840 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf"'
        ' -DEAST_BUILD_TYPE="release"'
    ),
]


def test_basic_app_release_behaviour(west_workplace, monkeypatch, mocker):
    """Running east release with no samples key, should skip build process for samples and
    build apps.
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


def test_basic_app_release_behaviour_no_samples_folder(
    west_workplace, monkeypatch, mocker
):
    """Running east release with no samples key and no samples folder should skip build
    process for samples and build apps.
    """
    project = west_workplace

    helpers.create_and_write(
        project,
        "east.yml",
        east_yaml_no_samples_key,
    )

    sh.rmtree(os.path.join(project, "samples"))

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project,
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
    """Running east release with no apps key, should skip build process for apps and build
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
    """Running east release with both apps and samples keys should run normally."""
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


east_yaml_no_build_types_key = """
apps:
  - name: test_one
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840
"""

expected_app_release_west_commands_no_build_types = [
    "build -b custom_nrf52840dk@1.0.0 app",
    "build -b custom_nrf52840dk@1.1.0 app",
    "build -b custom_nrf52840dk@2.20.1 app",
    "build -b nrf52840dk_nrf52840 app",
]


def test_basic_app_release_behaviour_no_build_type(west_workplace, monkeypatch, mocker):
    """Running east release on applications without any build types should just build
    apps.
    """
    project_path = west_workplace

    helpers.create_and_write(
        project_path,
        "east.yml",
        east_yaml_no_build_types_key,
    )

    monkeypatch.setattr(east.workspace_commands.release_commands, "RUNNING_TESTS", True)

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project_path,
        "release",
        expected_west_cmds=expected_app_release_west_commands_no_build_types,
    )


east_yaml_samples_no_build_types_key = """
apps:
  - name: test_one
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840

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

expected_app_samples_release_west_commands = [
    "build -b custom_nrf52840dk@1.0.0 app",
    "build -b custom_nrf52840dk@1.1.0 app",
    "build -b custom_nrf52840dk@2.20.1 app",
    "build -b nrf52840dk_nrf52840 app",
    "build -b custom_nrf52840dk@1.0.0 samples/settings",
    "build -b custom_nrf52840dk@1.1.0 samples/settings",
    "build -b custom_nrf52840dk@2.20.1 samples/settings",
    "build -b nrf52840dk_nrf52840 samples/settings",
    "build -b custom_nrf52840dk@1.0.0 samples/dfu",
    "build -b custom_nrf52840dk@1.1.0 samples/dfu",
    "build -b custom_nrf52840dk@2.20.1 samples/dfu",
    "build -b nrf52840dk_nrf52840 samples/dfu",
]


def test_basic_app_release_behaviour_no_build_type_with_samples(
    west_workplace, monkeypatch, mocker
):
    """Running east release on applications and samples without any build types should
    just build apps and samples.
    """
    project_path = west_workplace

    helpers.create_and_write(
        project_path,
        "east.yml",
        east_yaml_samples_no_build_types_key,
    )

    monkeypatch.setattr(east.workspace_commands.release_commands, "RUNNING_TESTS", True)

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project_path,
        "release",
        expected_west_cmds=expected_app_samples_release_west_commands,
    )


east_yaml_non_existing_sample = """
samples:
  - name: settings
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840

  - name: dfu
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840

  - name: non_existing_sample_name
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840
"""


def test_east_yml_with_non_existant_samples(
    west_workplace_parametrized, monkeypatch, mocker
):
    """Running east release when east.yml contains non-existing samples should abort before
    issuing any of the west build commands.
    """
    helpers.create_and_write(
        west_workplace_parametrized["project"],
        "east.yml",
        east_yaml_non_existing_sample,
    )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        west_workplace_parametrized["project"],
        "release",
        should_succed=False,
    )


east_yaml_non_existing_app = """
apps:
  - name: test_one
    west-boards:
      - nrf52840dk_nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf

  - name: test_two
    west-boards:
      - nrf52840dk_nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf

  - name: test_three_which_does_not_exist
    west-boards:
      - nrf52840dk_nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf
"""


def test_east_yml_with_non_existant_apps(west_workplace_multi_app, monkeypatch, mocker):
    """Running east release when east.yml contains non-existing apps should abort before
    issuing any of the west build commands. This only make sense in multi app
    workspaces.
    """
    project = west_workplace_multi_app

    helpers.create_and_write(
        project,
        "east.yml",
        east_yaml_non_existing_app,
    )

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project,
        "release",
        should_succed=False,
    )


east_yaml_single_app_simple = """
apps:
  - name: test_one
    west-boards:
      - nrf52840dk_nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf
"""

expected_single_app_release_west_commands = [
    (
        "build -b nrf52840dk_nrf52840 app/test_one -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf;conf/debug.conf"'
        ' -DEAST_BUILD_TYPE="debug"'
    ),
    (
        "build -b nrf52840dk_nrf52840 app/test_one -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf"'
        ' -DEAST_BUILD_TYPE="release"'
    ),
]


def test_building_app_that_is_not_on_the_first_level(
    west_workplace_multi_app, monkeypatch, mocker
):
    """Usecase: you have an `app` folder, with two projects inside it. `app_one`,
    is listed in east.yml, `app_two` is not. East should be able to build `app_one`
    without a problem.
    """
    project = west_workplace_multi_app

    helpers.create_and_write(
        project,
        "east.yml",
        east_yaml_single_app_simple,
    )

    monkeypatch.setattr(east.workspace_commands.release_commands, "RUNNING_TESTS", True)

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        project,
        "release",
        expected_west_cmds=expected_single_app_release_west_commands,
    )


east_yaml_hw_model_v2_only_apps = """
apps:
  - name: test_one
    west-boards:
      - custom/nrf52840dk
      - nrf52840dk/nrf52840
"""

expected_hw_v2_only_apps_release_west_commands = [
    "build -b custom/nrf52840dk@1.0.0 app",
    "build -b custom/nrf52840dk@1.1.0 app",
    "build -b custom/nrf52840dk@2.20.1 app",
    "build -b nrf52840dk/nrf52840 app",
]


def test_hw_model_v2_only_apps(west_workplace, monkeypatch, mocker):
    """Running east release with only apps key, where the board names are in the new
    hardware model v2 format.
    """
    helpers.create_and_write(
        west_workplace,
        "east.yml",
        east_yaml_hw_model_v2_only_apps,
    )

    monkeypatch.setattr(east.workspace_commands.release_commands, "RUNNING_TESTS", True)

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        west_workplace,
        "release",
        expected_west_cmds=expected_hw_v2_only_apps_release_west_commands,
    )


east_yaml_hw_model_v2_with_build_types = """
apps:
  - name: test_one
    west-boards:
      - nrf52840dk/nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf
"""

expected_hw_v2_with_build_types_release_west_commands = [
    (
        "build -b nrf52840dk/nrf52840 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf;conf/debug.conf"'
        ' -DEAST_BUILD_TYPE="debug"'
    ),
    (
        "build -b nrf52840dk/nrf52840 app -- -DCONF_FILE=conf/common.conf"
        ' -DOVERLAY_CONFIG="conf/nrf52840dk_nrf52840.conf"'
        ' -DEAST_BUILD_TYPE="release"'
    ),
]


def test_hw_model_v2_with_build_types(west_workplace, monkeypatch, mocker):
    """Running east release with build types, where the board names are in the new
    hardware model v2 format, should work.
    """
    helpers.create_and_write(
        west_workplace,
        "east.yml",
        east_yaml_hw_model_v2_with_build_types,
    )

    monkeypatch.setattr(east.workspace_commands.release_commands, "RUNNING_TESTS", True)

    helper_test_against_west_run(
        monkeypatch,
        mocker,
        west_workplace,
        "release",
        expected_west_cmds=expected_hw_v2_with_build_types_release_west_commands,
    )
