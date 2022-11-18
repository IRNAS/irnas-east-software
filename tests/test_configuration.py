import os

import pytest
from click.testing import CliRunner

from east.__main__ import cli
from east.east_context import EastContext
from east.east_yml import east_yml_load_error_msg, format_east_yml_load_error_msg

from . import helpers


def assert_all_is_none(east, path):
    """Small helper for brevity"""
    assert east.cwd == path
    assert east.west_dir_path is None
    assert east.detected_ncs_version is None
    assert east.project_dir is None


def test_good_west_workplace(west_workplace_parametrized):
    project_path = west_workplace_parametrized["project"]

    east = EastContext()
    assert east.cwd == project_path
    assert east.west_dir_path == os.path.dirname(project_path)
    assert east.detected_ncs_version == "v2.1.0"

    assert east.ncs_version_installed is False
    assert east.east_yml is None

    east.pre_workspace_command_check()
    assert east.ncs_version_installed is True
    assert east.east_yml is not None


def test_no_config_west_workplace(west_workplace_parametrized):
    project_path = west_workplace_parametrized["project"]
    os.remove(os.path.join(os.path.dirname(project_path), ".west", "config"))

    east = EastContext()
    assert_all_is_none(east, project_path)


def test_not_in_west_workplace(not_in_west_workplace):
    east = EastContext()
    assert_all_is_none(east, not_in_west_workplace)


def test_not_ncs_sdk_west_workplace(west_workplace_parametrized):
    project_path = west_workplace_parametrized["project"]

    helpers.west_no_nrf_sdk_in_yaml(os.path.dirname(project_path))

    east = EastContext()
    assert east.cwd == project_path
    assert east.west_dir_path == os.path.dirname(project_path)
    assert east.detected_ncs_version is None


def test_no_west_yaml_west_workplace(west_workplace_parametrized):
    project_path = west_workplace_parametrized["project"]

    os.remove(os.path.join(project_path, "west.yml"))

    east = EastContext()
    assert_all_is_none(east, project_path)


list_of_workspace_commands = [
    "build",
    "flash",
    "clean",
    "bypass",
    "release",
]


@pytest.mark.parametrize("workspace_command", list_of_workspace_commands)
def test_no_east_yaml_west_workplace(west_workplace_parametrized, workspace_command):
    project_path = west_workplace_parametrized["project"]
    os.remove(os.path.join(project_path, "east.yml"))

    # Detection of east.yml needs to be done in every west_workplace command, clean is
    # used here as an example
    runner = CliRunner()
    result = runner.invoke(cli, [workspace_command])

    assert result.exit_code == 1
    helpers.assert_strings_equal(
        result.output, format_east_yml_load_error_msg(east_yml_load_error_msg)
    )
