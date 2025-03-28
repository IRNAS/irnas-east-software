import copy
import os

import pytest

from east.east_yml import EastYmlLoadError, load_east_yml
from east.workspace_commands.pack_commands import ArtifactsToPack, TSuite, TSuiteError

from . import helpers

pack_yaml_single_app = """
pack:
  artifacts:
    - $APP_DIR/zephyr/merged.hex
  projects:
    - name: app.prod
      artifacts:
        - $APP_DIR/zephyr/zephyr.hex
        - dfu_application.zip
"""


def test_simple_pack_config(west_workplace):
    """Test a simple pack configuration."""
    project_path = west_workplace

    helpers.create_and_write(
        project_path,
        "east.yml",
        pack_yaml_single_app,
    )

    east_yaml = load_east_yml(project_path)

    assert east_yaml is not None
    assert east_yaml["pack"]["artifacts"] == ["$APP_DIR/zephyr/merged.hex"]
    assert east_yaml["pack"]["projects"][0]["name"] == "app.prod"
    assert east_yaml["pack"]["projects"][0]["artifacts"] == [
        "$APP_DIR/zephyr/zephyr.hex",
        "dfu_application.zip",
    ]


pack_yaml_multiple_apps = """
pack:
  projects:
    - name: app.prod
      artifacts:
        - $APP_DIR/zephyr/zephyr.hex
        - dfu_application.zip
    - name: app.rtt
      artifacts:
        - $APP_DIR/zephyr/zephyr.hex
        - dfu_application.zip
    - name: app.dev
      artifacts:
        - $APP_DIR/zephyr/zephyr.hex
        - dfu_application.zip
"""


def test_multiple_apps(west_workplace):
    """Test multiple apps."""
    project_path = west_workplace

    expected_app_names = ["app.prod", "app.rtt", "app.dev"]

    helpers.create_and_write(
        project_path,
        "east.yml",
        pack_yaml_multiple_apps,
    )

    east_yaml = load_east_yml(project_path)
    assert east_yaml is not None

    for i, app in enumerate(east_yaml["pack"]["projects"]):
        assert app["name"] == expected_app_names[i]
        assert app["artifacts"] == ["$APP_DIR/zephyr/zephyr.hex", "dfu_application.zip"]


pack_yaml_multiple_duplicated_apps = """
pack:
  projects:
    - name: app.prod
      artifacts:
        - $APP_DIR/zephyr/zephyr.hex
        - dfu_application.zip
    - name: app.prod
      artifacts:
        - $APP_DIR/zephyr/zephyr.hex
        - dfu_application.zip
"""


def test_duplicated_multiple_apps(west_workplace):
    """Test that duplicated project names raise an exception."""
    project_path = west_workplace

    helpers.create_and_write(
        project_path,
        "east.yml",
        pack_yaml_multiple_duplicated_apps,
    )

    with pytest.raises(EastYmlLoadError):
        load_east_yml(project_path)


pack_yaml_two_artifact_fields = """
pack:
  projects:
    - name: app.prod
      artifacts:
        - $APP_DIR/zephyr/zephyr.hex
        - dfu_application.zip
      overwrite_artifacts:
        - $APP_DIR/zephyr/zephyr.hex
        - dfu_application.zip
        - dfu_application123.zip
    - name: app.rtt
      artifacts:
        - $APP_DIR/zephyr/zephyr.hex
        - dfu_application.zip
"""


def test_that_two_artifact_related_fields_raise_an_error(west_workplace):
    """Test that if both artifact and overwrite_artifacts fields are in the same
    project that exception is raised.
    """
    project_path = west_workplace

    helpers.create_and_write(
        project_path,
        "east.yml",
        pack_yaml_multiple_duplicated_apps,
    )

    with pytest.raises(EastYmlLoadError):
        load_east_yml(project_path)


pack_yaml_duplicated_artifact_fields1 = """
pack:
  artifacts:
    - $APP_DIR/zephyr/zephyr.hex
  projects:
    - name: app.prod
      artifacts:
        - $APP_DIR/zephyr/zephyr.hex
        - dfu_application.zip
"""

pack_yaml_duplicated_artifact_fields2 = """
pack:
  artifacts:
    - $APP_DIR/zephyr/zephyr.hex
    - $APP_DIR/zephyr/zephyr.hex
  projects:
    - name: app.prod
      artifacts:
        - $APP_DIR/zephyr/merged.hex
        - dfu_application.zip
"""

pack_yaml_duplicated_artifact_fields3 = """
pack:
  artifacts:
    - $APP_DIR/zephyr/zephyr.hex
  projects:
    - name: app.prod
      overwrite_artifacts:
        - $APP_DIR/zephyr/merged.hex
        - $APP_DIR/zephyr/merged.hex
"""


def test_that_duplicated_artifacts_raise_an_error(west_workplace):
    """Test that if both artifact and overwrite_artifacts fields are in the same
    project that exception is raised.
    """
    project_path = west_workplace

    for pack_yaml in [
        pack_yaml_duplicated_artifact_fields1,
        pack_yaml_duplicated_artifact_fields2,
        pack_yaml_duplicated_artifact_fields3,
    ]:
        helpers.create_and_write(
            project_path,
            "east.yml",
            pack_yaml,
        )

        with pytest.raises(EastYmlLoadError):
            load_east_yml(project_path)


test_suite_json = {
    "name": "app/app.prod",
    "arch": "arm",
    "platform": "custom_board@1.0.0/nrf52840",
    "path": "../project/app",
    "run_id": "953b256c22f70c8293b9b625baea26ee",
    "runnable": False,
    "retries": 0,
    "status": "passed",
    "execution_time": "0.00",
    "build_time": "26.15",
    "testcases": [
        {
            "identifier": "app.prod",
            "execution_time": "0.00",
            "status": "skipped",
            "reason": "Test was built only",
        }
    ],
}


def test_creating_a_tsuite_instance():
    """Test creating a TSuite instance.

    GIVEN a testsuite JSON object,
    WHEN creating a TSuite instance,
    THEN then the instance should have the correct attributes.
    """
    ts = TSuite.from_dict(test_suite_json)

    assert ts.name == "app.prod"
    assert ts.board == "custom_board@1.0.0_nrf52840"
    assert ts.twister_out_path == os.path.join(ts.board, test_suite_json["name"])
    assert ts.pack_path == os.path.join(ts.name, ts.board)


def test_raising_expection_for_a_not_ok_testsuite_status():
    """Test checking for a not OK testsuite status.

    GIVEN a testsuite JSON object with status different from "passed",
    WHEN creating a TSuite instance,
    THEN then the expection should be raised.
    """
    bad_test_suite_json = copy.deepcopy(test_suite_json)
    bad_test_suite_json["status"] = "failed"

    with pytest.raises(TSuiteError):
        _ = TSuite.from_dict(bad_test_suite_json)


def test_raising_expection_for_a_bad_testsuite_json():
    """Test checking for a bad testsuite json.

    testsuite json is considered bad if doesn't contain all keys expected by the TSuite
    class.

    GIVEN a testsuite JSON object with missing keys
    WHEN creating a TSuite instance,
    THEN then the expection should be raised.
    """
    with pytest.raises(TSuiteError):
        _ = TSuite.from_dict({})


def helper_get_pack_yaml_from_east_yml(project_path: str, east_yml: str):
    helpers.create_and_write(
        project_path,
        "east.yml",
        east_yml,
    )

    east_yaml = load_east_yml(project_path)

    assert east_yaml is not None

    return east_yaml["pack"]


def test_getting_artifact_list_for_a_listed_project(west_workplace):
    """Test getting a list of artifacts for a project that is listed in the east.yml.

    GIVEN a pack configuration with a single project,
    WHEN getting the list of artifacts for a listed project,
    THEN the returned list should contain common and project-specific artifacts.
    """
    pack_yaml = helper_get_pack_yaml_from_east_yml(west_workplace, pack_yaml_single_app)

    atp = ArtifactsToPack.from_east_yml_pack_field(pack_yaml)

    arts = atp.get_artifacts_for_project("app.prod")

    assert arts == [
        "$APP_DIR/zephyr/merged.hex",
        "$APP_DIR/zephyr/zephyr.hex",
        "dfu_application.zip",
    ]


def test_getting_artifact_list_for_a_unlisted_project(west_workplace):
    """Test getting a list of artifacts for a project that is not listed in the
    east.yml.

    GIVEN a pack configuration with a single project,
    WHEN getting the list of artifacts for a unlisted project,
    THEN the returned list should contain only common aritfacts.
    """
    pack_yaml = helper_get_pack_yaml_from_east_yml(west_workplace, pack_yaml_single_app)

    atp = ArtifactsToPack.from_east_yml_pack_field(pack_yaml)

    arts = atp.get_artifacts_for_project("app.krneki")

    assert arts == [
        "$APP_DIR/zephyr/merged.hex",
    ]


# TODO: tests related to the Artifacts class
# 1. Check if the rename method works correctly
# 2. Provide "good inputs" and check if self.src_dir_pairs is correctly populated
# 3. Implement and test existance check for the source files, for this you will need to
# setup a temporary directory with some files in it.
# 4. Implement and test the duplication check for the destination files
# 5. Implement and test the copy method, some temporary directory will be needed.

# As a full e2e test, you need to creata a fake twister_out dir and run east pack on it
# and then check output.
# You can mock the gen_version function (that you still need to implement).
# Clean up TODOs in the code.
# Move smaller classes to their own files, as well as their tests. (maybe a single unit
# for this one)?
# Add GIVEN, WHEN, THEN comments to all tests.
