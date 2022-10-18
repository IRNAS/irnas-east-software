import os

from east.east_context import EastContext


def assert_all_is_none(east, path):
    """Small helper for brevity"""
    assert east.cwd == path
    assert east.west_dir_path is None
    assert east.detected_ncs_version is None
    assert east.project_dir is None


def test_good_west_workplace(west_workplace):
    project_path = west_workplace

    east = EastContext()
    assert east.cwd == project_path
    assert east.west_dir_path == os.path.dirname(project_path)
    assert east.detected_ncs_version == "v2.1.0"


def test_no_config_west_workplace(no_config_west_workplace):
    project_path = no_config_west_workplace

    east = EastContext()
    assert_all_is_none(east, project_path)


def test_not_in_west_workplace(not_in_west_workplace):
    east = EastContext()
    assert_all_is_none(east, not_in_west_workplace)


def test_not_ncs_sdk_west_workplace(not_ncs_sdk_west_workplace):
    project_path = not_ncs_sdk_west_workplace

    east = EastContext()
    assert east.cwd == project_path
    assert east.west_dir_path == os.path.dirname(project_path)
    assert east.detected_ncs_version is None


def test_no_west_yaml_west_workplace(no_westyaml_west_workplace):
    project_path = no_westyaml_west_workplace
    east = EastContext()
    assert_all_is_none(east, project_path)
