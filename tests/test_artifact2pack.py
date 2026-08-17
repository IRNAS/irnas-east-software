import yaml

from east.modules.artifacts2pack import ArtifactsToPack

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


def test_getting_artifact_list_for_listed_project():
    """Test getting a list of artifacts for the that is listed in the east.yml."""
    atp = ArtifactsToPack.from_east_yml(yaml.safe_load(pack_yaml_single_app))

    arts = atp.get_artifacts_for_project("app.prod")

    assert arts == [
        "$APP_DIR/zephyr/merged.hex",
        "$APP_DIR/zephyr/zephyr.hex",
        "dfu_application.zip",
    ]


def test_getting_artifact_list_for_unlisted_project():
    """Test getting a list of artifacts for the project that isn't listed in the east.yml."""
    atp = ArtifactsToPack.from_east_yml(yaml.safe_load(pack_yaml_single_app))

    arts = atp.get_artifacts_for_project("app.krneki")

    assert arts == [
        "$APP_DIR/zephyr/merged.hex",
    ]


pack_yaml_overwrite_then_nrfutil_only = """
pack:
  artifacts:
    - $APP_DIR/zephyr/zephyr.elf
    - $APP_DIR/zephyr/zephyr.bin
  build_configurations:
    - name: app.prod
      nrfutil_flash_pack: True
    - name: app.native_sim
      overwrite_artifacts:
        - $APP_DIR/zephyr/zephyr.exe
    - name: samples.factory_setup_usb
      nrfutil_flash_pack: True
    - name: samples.dev
      artifacts:
        - dfu_application.zip
    - name: samples.factory_setup_rtt
      nrfutil_flash_pack: True
"""


def test_that_build_config_order_does_not_leak_artifacts():
    """Build configurations with only 'nrfutil_flash_pack' must use common artifacts.

    Previously the artifact list was carried over from the previous build
    configuration in the loop, which meant that entries with only
    'nrfutil_flash_pack: True' inherited the artifacts of the entry above them.
    """
    atp = ArtifactsToPack.from_east_yml(
        yaml.safe_load(pack_yaml_overwrite_then_nrfutil_only)
    )

    common = ["$APP_DIR/zephyr/zephyr.elf", "$APP_DIR/zephyr/zephyr.bin"]

    assert atp.get_artifacts_for_project("app.prod") == common
    assert atp.get_artifacts_for_project("app.native_sim") == [
        "$APP_DIR/zephyr/zephyr.exe"
    ]
    # This one is directly after the 'overwrite_artifacts' entry.
    assert atp.get_artifacts_for_project("samples.factory_setup_usb") == common
    assert atp.get_artifacts_for_project("samples.dev") == common + [
        "dfu_application.zip"
    ]
    # This one is directly after an 'artifacts' entry.
    assert atp.get_artifacts_for_project("samples.factory_setup_rtt") == common


def test_that_projects_do_not_share_artifact_list_objects():
    """Each project must own its artifact list, so mutating one doesn't affect others."""
    atp = ArtifactsToPack.from_east_yml(
        yaml.safe_load(pack_yaml_overwrite_then_nrfutil_only)
    )

    lists = [id(p.artifacts) for p in atp.projects]
    lists.append(id(atp.common_artifacts))

    assert len(lists) == len(set(lists))
