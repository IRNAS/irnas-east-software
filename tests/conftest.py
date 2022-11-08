import os

import pytest

import east.east_context

from . import helpers

# This is a conftest.py file, which has a special meaning when used with pytest.
#
# From pytest documentation:
#
# The conftest.py file serves as a means of providing fixtures for an entire directory.
# Fixtures defined in a conftest.py can be used by any test in that package without
# needing to import them (pytest will automatically discover them).
#
# IMPORTANT:
# fixtures with autouse=True are always run when tests are run.
# Other fixtures needs to explicitly mentioned in the arguments of the test.


@pytest.fixture()
def patch_constants(tmpdir_factory, monkeypatch):
    """Patch all east constants.

    This patch will move all constants under path provided by tmpdir_factory, thus
    basically creating a new environment in which we can test. That way can not override
    existing packages on the system.

    IMPORTANT: Currently unused, however it might be useful in the future.
    """
    p = tmpdir_factory.mktemp("test_dir")

    for k, v in east.east_context.const_paths.items():
        monkeypatch.setitem(east.east_context.const_paths, k, p + v)

    # Return this new path
    return p


@pytest.fixture(autouse=True)
def disable_rich_markup(monkeypatch):
    """Disable rich markup in east context init method.

    Needed in all tests, if rich markup is enabled is impossible to do comparisons
    between hard-coded rich style messages and shell's stdout.

    Args:
        monkeypatch ():     Fixture
    """
    monkeypatch.setattr(east.east_context, "RICH_CONSOLE_ENABLE_MARKUP", False)


def west_workplace_fixture_common(west_top_dir, monkeypatch, mocker):
    """Main level fixture for tests for app workspace.

    This is split so the west_top_dir dir is created separately by the callers.

    Creates a west_workplace folder on the temporary path, creates inside a set of
    folders and files expected by west and east and changes to the project directory.

    It is not expected that tests will directly use this fixture.

    Args:
        tmp_path_factory ():
        monkeypatch ():

    Returns:
        Project path
    """

    project_path = helpers.create_good_west(west_top_dir)

    # # We pretend that
    def mocked_check_exe(self, exe):
        if exe == self.consts["nrf_toolchain_manager_path"]:
            return True

    def mocked_run_manager(self, command, **kwargs):
        if command == "list":
            return ["v2.0.0", "v2.1.0"]

    mocker.patch("east.east_context.EastContext.check_exe", mocked_check_exe)
    mocker.patch("east.east_context.EastContext.run_manager", mocked_run_manager)

    monkeypatch.chdir(project_path)
    return project_path


@pytest.fixture()
def west_workplace_fixture(tmp_path_factory, monkeypatch, mocker):
    """Main level fixture for tests for single app workspace.

    Returns:
        Project path
    """
    west_top_dir = tmp_path_factory.mktemp("west_workplace")
    return west_workplace_fixture_common(west_top_dir, monkeypatch, mocker)


@pytest.fixture()
def west_workplace_fixture_multi(tmp_path_factory, monkeypatch, mocker):
    """Main level fixture for tests for multi app workspace.

    Returns:
        Project path
    """
    west_top_dir = tmp_path_factory.mktemp("west_workplace")
    return west_workplace_fixture_common(west_top_dir, monkeypatch, mocker)


@pytest.fixture()
def west_workplace(west_workplace_fixture):
    project_path = west_workplace_fixture
    return project_path


@pytest.fixture()
def no_config_west_workplace(west_workplace_fixture):
    project_path = west_workplace_fixture
    os.remove(os.path.join(os.path.dirname(project_path), ".west", "config"))
    return project_path


@pytest.fixture()
def no_westyaml_west_workplace(west_workplace_fixture):
    project_path = west_workplace_fixture
    os.remove(os.path.join(project_path, "west.yml"))
    return project_path


@pytest.fixture()
def not_in_west_workplace(tmp_path_factory, monkeypatch):
    path = tmp_path_factory.mktemp("not_west_workplace")
    monkeypatch.chdir(path)
    return str(path)


@pytest.fixture()
def not_ncs_sdk_west_workplace(west_workplace_fixture):
    project_path = west_workplace_fixture
    helpers.west_no_nrf_sdk_in_yaml(os.path.dirname(project_path))
    return project_path


@pytest.fixture()
def west_workplace_multi_app(west_workplace_fixture_multi):
    project_path = west_workplace_fixture_multi
    helpers.create_good_west_multi_app(os.path.dirname(project_path))
    return project_path


@pytest.fixture()
def no_eastyaml_west_workplace(west_workplace_fixture):
    project_path = west_workplace_fixture

    os.remove(os.path.join(project_path, "east.yml"))
    return project_path
