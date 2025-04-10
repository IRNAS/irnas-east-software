import yaml
from east.modules.artifacts2pack import ArtifactsToPack

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


def test_getting_artifact_list_for_a_listed_project():
    """Test getting a list of artifacts for a project that is listed in the east.yml."""
    atp = ArtifactsToPack.from_east_yml(yaml.safe_load(pack_yaml_single_app))

    arts = atp.get_artifacts_for_project("app.prod")

    assert arts == [
        "$APP_DIR/zephyr/merged.hex",
        "$APP_DIR/zephyr/zephyr.hex",
        "dfu_application.zip",
    ]


def test_getting_artifact_list_for_a_unlisted_project():
    """Test getting a list of artifacts for a project that isn't listed in the east.yml."""
    atp = ArtifactsToPack.from_east_yml(yaml.safe_load(pack_yaml_single_app))

    arts = atp.get_artifacts_for_project("app.krneki")

    assert arts == [
        "$APP_DIR/zephyr/merged.hex",
    ]
