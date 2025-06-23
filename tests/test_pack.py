import os

import pytest
from click.testing import CliRunner

from east.__main__ import cli
from east.east_yml import EastYmlLoadError, load_east_yml

from .helpers import create_and_write

pack_yaml_single_app = """
pack:
  artifacts:
    - $APP_DIR/zephyr/merged.hex
  build_configurations:
    - name: app.prod
      artifacts:
        - $APP_DIR/zephyr/zephyr.hex
        - dfu_application.zip
"""


def test_simple_pack_config(west_workplace):
    """Test a simple pack configuration."""
    project_path = west_workplace

    create_and_write(
        project_path,
        "east.yml",
        pack_yaml_single_app,
    )

    east_yaml = load_east_yml(project_path)

    assert east_yaml is not None
    assert east_yaml["pack"]["artifacts"] == ["$APP_DIR/zephyr/merged.hex"]
    assert east_yaml["pack"]["build_configurations"][0]["name"] == "app.prod"
    assert east_yaml["pack"]["build_configurations"][0]["artifacts"] == [
        "$APP_DIR/zephyr/zephyr.hex",
        "dfu_application.zip",
    ]


pack_yaml_multiple_apps = """
pack:
  build_configurations:
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

    create_and_write(
        project_path,
        "east.yml",
        pack_yaml_multiple_apps,
    )

    east_yaml = load_east_yml(project_path)
    assert east_yaml is not None

    for i, app in enumerate(east_yaml["pack"]["build_configurations"]):
        assert app["name"] == expected_app_names[i]
        assert app["artifacts"] == ["$APP_DIR/zephyr/zephyr.hex", "dfu_application.zip"]


pack_yaml_multiple_duplicated_apps = """
pack:
  build_configurations:
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

    create_and_write(
        project_path,
        "east.yml",
        pack_yaml_multiple_duplicated_apps,
    )

    with pytest.raises(EastYmlLoadError):
        load_east_yml(project_path)


pack_yaml_two_artifact_fields = """
pack:
  build_configurations:
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

    create_and_write(
        project_path,
        "east.yml",
        pack_yaml_two_artifact_fields,
    )

    with pytest.raises(EastYmlLoadError):
        load_east_yml(project_path)


pack_yaml_duplicated_artifact_fields1 = """
pack:
  artifacts:
    - $APP_DIR/zephyr/zephyr.hex
  build_configurations:
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
  build_configurations:
    - name: app.prod
      artifacts:
        - $APP_DIR/zephyr/merged.hex
        - dfu_application.zip
"""

pack_yaml_duplicated_artifact_fields3 = """
pack:
  artifacts:
    - $APP_DIR/zephyr/zephyr.hex
  build_configurations:
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
        create_and_write(
            project_path,
            "east.yml",
            pack_yaml,
        )

        with pytest.raises(EastYmlLoadError):
            load_east_yml(project_path)


east_pack_file = """
pack:
  artifacts:
    - $APP_DIR/zephyr/zephyr.hex
    - $APP_DIR/zephyr/zephyr.bin
    - merged.hex
  build_configurations:
    - name: sample.basic.blinky
      overwrite_artifacts:
        - $APP_DIR/zephyr/zephyr.hex
        - $APP_DIR/zephyr/zephyr.bin
  extra:
    - test-extra/extra_script.sh
"""


def test_pack_command(west_workplace, mocker):
    """Test the pack command.

    This is a full e2e test that runs the pack command on temp workspace and checks
    that all files that were actually copied and created.

    This test depends on the the content of the helpers.py::_create_good_west_workspace
    function.
    """
    project_path = west_workplace

    # Overwrite the existing east.yml file with the new one.
    create_and_write(
        project_path,
        "east.yml",
        east_pack_file,
    )

    mocker.patch(
        "east.helper_functions.get_raw_git_describe_output",
        return_value="v1.0.0-0-g1234567",
    )

    # Run pack command
    runner = CliRunner()
    result = runner.invoke(cli, ["pack", "--pack-path", "test_pack"])
    assert result.exit_code == 0

    # Find all files in the pack directory
    all_files = []
    for root, _, files in os.walk(os.path.join(project_path, "test_pack")):
        for file in files:
            all_files.append(os.path.join(root, file))

    # Remove common prefix from all files
    commonprefix = os.path.commonprefix(all_files)
    all_files = [x[len(commonprefix) :] for x in all_files]

    # sort the files for easier comparison
    all_files.sort()

    # We expect the following files to be added to the pack directory:
    expected_files = [
        "app.prod-v1.0.0.zip",
        "sample.basic.blinky-v1.0.0.zip",
        "sample.basic.blinky/custom_board@1.0.0_nrf52840/sample.basic.blinky-zephyr-v1.0.0.bin",
        "sample.basic.blinky/custom_board@1.0.0_nrf52840/sample.basic.blinky-zephyr-v1.0.0.hex",
        "app.prod/custom_board@1.0.0_nrf52840/app.prod-zephyr-v1.0.0.bin",
        "app.prod/custom_board@1.0.0_nrf52840/app.prod-merged-v1.0.0.hex",
        "app.prod/custom_board@1.0.0_nrf52840/app.prod-zephyr-v1.0.0.hex",
        "extra-v1.0.0.zip",
        "extra/extra_script-v1.0.0.sh",
    ]
    expected_files.sort()

    assert all_files == expected_files
