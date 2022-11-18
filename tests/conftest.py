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
        _ = self
        _ = kwargs

        if command == "list":
            return ["v2.0.0", "v2.1.0"]

    mocker.patch("east.east_context.EastContext.check_exe", mocked_check_exe)
    mocker.patch("east.east_context.EastContext.run_manager", mocked_run_manager)

    monkeypatch.chdir(project_path)
    return project_path


@pytest.fixture()
def west_workplace(tmp_path_factory, monkeypatch, mocker):
    """Main level fixture for tests for single app workspace.

    Returns:
        Project path
    """
    west_top_dir = tmp_path_factory.mktemp("west_workplace")
    return west_workplace_fixture_common(west_top_dir, monkeypatch, mocker)


@pytest.fixture()
def west_workplace_multi_app(tmp_path_factory, monkeypatch, mocker):
    """Main level fixture for tests for multi app workspace.

    Returns:
        Project path
    """
    west_top_dir = tmp_path_factory.mktemp("west_workplace")
    project_path = west_workplace_fixture_common(west_top_dir, monkeypatch, mocker)
    helpers.create_good_west_multi_app(os.path.dirname(project_path))
    return project_path


@pytest.fixture()
def not_in_west_workplace(tmp_path_factory, monkeypatch):
    """Creates a temp workspace without anything and changes to it.

        tmp_path_factory ():
        monkeypatch ():

    Returns:
        Path
    """
    path = tmp_path_factory.mktemp("not_west_workplace")
    monkeypatch.chdir(path)
    return str(path)


@pytest.fixture(params=["single", "multi"])
def west_workplace_parametrized(tmp_path_factory, monkeypatch, mocker, request):
    """Parametrized west workspace fixture for single and multi app.

    By using it in the tests the tests are executed twice as many, first for the single
    app workspace and then for multi app workspace.

    The return dictionary contains all keys that the test should need.

    Use this fixture when behaviour under test should be the same in both single and
    multi app setup.

        tmp_path_factory ():
        monkeypatch ():
        mocker ():
        request ():

    Returns:
        Dict with project, app and prefix paths for testing.
    """

    west_top_dir = tmp_path_factory.mktemp("west_workplace")
    project_path = west_workplace_fixture_common(west_top_dir, monkeypatch, mocker)

    app_path = os.path.join(project_path, "app")
    prefix_path = "../../app/"

    if request.param == "multi":
        helpers.create_good_west_multi_app(os.path.dirname(project_path))
        app_path = os.path.join(project_path, "app", "test_one")
        prefix_path = "../../app/test_one/"

    return {"project": project_path, "app": app_path, "prefix": prefix_path}
