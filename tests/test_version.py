import os

import pytest
from click.testing import CliRunner

from east.__main__ import cli
from east.east_yml import EastYmlLoadError, load_east_yml

from .helpers import create_and_write

two_apps = """
version:
  paths:
    - app/test_one
    - app/test_two
"""


def test_simple_version_config(west_workplace):
    """Test a simple version config."""
    project_path = west_workplace

    create_and_write(
        project_path,
        "east.yml",
        two_apps,
    )

    east_yaml = load_east_yml(project_path)
    assert east_yaml is not None

    paths = east_yaml["version"]["paths"]
    assert paths == ["app/test_one", "app/test_two"]


two_duplicated_apps = """
version:
  paths:
    - app/test_one
    - app/test_one
"""


def test_simple_pack_config(west_workplace):
    """Test a simple pack configuration."""
    project_path = west_workplace

    create_and_write(
        project_path,
        "east.yml",
        two_duplicated_apps,
    )

    with pytest.raises(EastYmlLoadError):
        load_east_yml(project_path)


expected_version_file = """
VERSION_MAJOR = 1
VERSION_MINOR = 2
PATCHLEVEL = 3
VERSION_TWEAK = 0
"""


def test_basic_case(mocker, monkeypatch, west_workplace_multi_app):
    """Test creating two version files that are specified in the east yaml file."""
    project_path = west_workplace_multi_app

    # Below output corresponds to the case where HEAD is directly on tagged commit
    infra = {
        "mocker": mocker,
        "monkeypatch": monkeypatch,
        "path": project_path,
        "git": "v1.2.3-0-g98bddf3",
        "east_yml": two_apps,
    }

    helper_run_cmd(infra, "util version")

    paths = [
        os.path.join(project_path, "app/test_one", "VERSION"),
        os.path.join(project_path, "app/test_two", "VERSION"),
    ]

    for p in paths:
        helper_assert_file_content(p, expected_version_file)


def test_overriding_tag_on_cmd(mocker, monkeypatch, west_workplace_multi_app):
    """Test giving tag as an cmd arg."""
    project_path = west_workplace_multi_app

    # Below output corresponds to the case where HEAD is directly on tagged commit
    infra = {
        "mocker": mocker,
        "monkeypatch": monkeypatch,
        "path": project_path,
        "git": "v1.2.5-0-g98bddf3",
        "east_yml": two_apps,
    }

    helper_run_cmd(infra, "util version --tag v1.2.3")

    paths = [
        os.path.join(project_path, "app/test_one", "VERSION"),
        os.path.join(project_path, "app/test_two", "VERSION"),
    ]

    for p in paths:
        helper_assert_file_content(p, expected_version_file)


def test_overriding_paths_on_cmd(mocker, monkeypatch, west_workplace_multi_app):
    """Test giving path as an cmd arg."""
    project_path = west_workplace_multi_app

    # Below output corresponds to the case where HEAD is directly on tagged commit
    infra = {
        "mocker": mocker,
        "monkeypatch": monkeypatch,
        "path": project_path,
        "git": "v1.2.3-0-g98bddf3",
        "east_yml": two_apps,
    }

    helper_run_cmd(infra, "util version .")

    helper_assert_file_content(
        os.path.join(project_path, "VERSION"), expected_version_file
    )


def test_overriding_tag_and_paths_on_cmd(mocker, monkeypatch, west_workplace_multi_app):
    """Test giving version and paths as an cmd arg."""
    project_path = west_workplace_multi_app

    # Below output corresponds to the case where HEAD is directly on tagged commit
    infra = {
        "mocker": mocker,
        "monkeypatch": monkeypatch,
        "path": project_path,
        "git": "v1.2.5-0-g98bddf3",
        "east_yml": two_apps,
    }

    helper_run_cmd(infra, "util version --tag v1.2.3 . samples tests")

    paths = [
        os.path.join(project_path, "VERSION"),
        os.path.join(project_path, "samples", "VERSION"),
        os.path.join(project_path, "tests", "VERSION"),
    ]

    for p in paths:
        helper_assert_file_content(p, expected_version_file)


def helper_assert_file_content(path, expected_content):
    """Helper function to assert file content."""
    assert os.path.isfile(path)

    with open(path) as file:
        assert file.read() == expected_content.strip()


def helper_run_cmd(infra, east_cmd):
    """Helper function to test the CLI command."""
    create_and_write(
        infra["path"],
        "east.yml",
        infra["east_yml"],
    )

    runner = CliRunner()

    # Mock output of git command, so tests do not have to depend on it
    infra["mocker"].patch(
        "east.helper_functions.get_raw_git_describe_output",
        return_value=infra["git"],
    )

    infra["monkeypatch"].chdir(infra["path"])

    result = runner.invoke(cli, east_cmd.strip().split(), catch_exceptions=False)
    assert result.exit_code == 0
