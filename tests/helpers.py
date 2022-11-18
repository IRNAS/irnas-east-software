import os
import shutil

west_config_content = """
[manifest]
path = project
file = west.yml

[zephyr]
base = zephyr
"""
nrfsdk_yaml_content = """
manifest:
  self:
    # This repository should be cloned to
    path: project

  remotes:
    - name: nrfconnect
      url-base: https://github.com/nrfconnect

  projects:
    # the NCS repository
    - name: nrf
      repo-path: sdk-nrf
      remote: nrfconnect
      revision: v2.1.0
      import: true

    - name: zephyr
      remote: nrfconnect
      repo-path: sdk-zephyr
      revision: v3.1.99-ncs1
      import: true
"""

zephyrsdk_yaml_content = """
manifest:
  self:
    path: example-application
    west-commands: scripts/west-commands.yml

  remotes:
    - name: zephyrproject-rtos
      url-base: https://github.com/zephyrproject-rtos

  projects:
    - name: zephyr
      remote: zephyrproject-rtos
      revision: main
      import: true
"""

east_yaml_single_app = """
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

samples:
  - name: settings
    west-boards:
      - custom_nrf52840dk
    inherit-build-type:
        app: test_one
        build-type: debug

  - name: dfu
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840
    # Don't inherit, use prj.conf in the sample's folder.
"""

east_yaml_multiple_apps = """
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

  - name: test_two
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840

    build-types:
      - type: debug
        conf-files:
          - debug.conf
      - type: rtt
        conf-files:
          - rtt.conf
      - type: debug-rtt
        conf-files:
          - debug.conf
          - rtt.conf

samples:
  - name: settings
    west-boards:
      - custom_nrf52840dk
    inherit-build-type:
        app: test_one
        build-type: debug

  - name: dfu
    west-boards:
      - custom_nrf52840dk
      - nrf52840dk_nrf52840
    # Don't inherit, use prj.conf in the sample's folder.
"""


def create_and_write(path: str, filename: str, content: str):
    """Create a file in the given path with the given content.

    Args:
        path (str):         Path from where to create the filename
        filename (str):     Filename can be either a direct file name such as a file.txt
                            or a longer path, such as dir_a/dir_b/file.txt
        content (str):      Content that will be written.

    """
    filepath = os.path.join(path, filename)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def _delete_all_in(path: str):
    """Deletes all files in given path.

    path (str):
    """
    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print("Failed to delete %s. Reason: %s" % (file_path, e))


dummy_config = """
CONFIG_DEBUG=y
"""


def _create_good_west_workspace(west_top_dir):
    """
    Main function, which will create correct west workspace. All other 'bad'
    functions will just delete from it.
    """
    os.mkdir(os.path.join(west_top_dir, "project"))
    os.mkdir(os.path.join(west_top_dir, "project/app"))
    os.mkdir(os.path.join(west_top_dir, "project/samples"))
    os.mkdir(os.path.join(west_top_dir, "project/samples/settings"))
    os.mkdir(os.path.join(west_top_dir, "project/samples/dfu"))
    os.mkdir(os.path.join(west_top_dir, "zephyr"))

    create_and_write(west_top_dir, ".west/config", west_config_content)
    create_and_write(west_top_dir, "project/west.yml", nrfsdk_yaml_content)
    create_and_write(west_top_dir, "project/east.yml", east_yaml_single_app)
    create_and_write(
        west_top_dir, "project/app/conf/nrf52840dk_nrf52840.conf", dummy_config
    )

    return os.path.join(west_top_dir, "project")


def create_good_west(west_top_dir):
    """Creates a correct west workspace in west_top_dir.

    Args:
        west_top_dir (str): Path to west top dir.

    Returns:
        Path to the project inside west top dir.
    """
    return _create_good_west_workspace(west_top_dir)


def create_good_west_multi_app(west_top_dir):
    """Creates a correct west workspace in west_top_dir, with multi app east yaml

    Args:
        west_top_dir (str): Path to west top dir.

    Returns:
        Path to the project inside west top dir.
    """
    create_and_write(west_top_dir, "project/east.yml", east_yaml_multiple_apps)
    os.makedirs(os.path.join(west_top_dir, "project/app/test_one"), exist_ok=True)
    os.makedirs(os.path.join(west_top_dir, "project/app/test_two"), exist_ok=True)
    create_and_write(
        west_top_dir, "project/app/test_one/conf/nrf52840dk_nrf52840.conf", dummy_config
    )


def west_no_nrf_sdk_in_yaml(west_top_dir):
    """Creates a west workspace without nrf-sdk in west.yaml

    Args:
        west_top_dir (): Path to west top dir.
    """
    create_and_write(west_top_dir, ".west/config", west_config_content)
    create_and_write(west_top_dir, "project/west.yml", zephyrsdk_yaml_content)


def assert_strings_equal(string1: str, string2: str):
    """Helper that should be used when comparing strings that come from east's stdout
    and east's internal hardcoded strings.

    Args:
        string1 (str):
        string2 (str):

    Returns:
        Asserts if strings are different
    """

    def clear_rich(string):
        """Output from runner.invoke and hard-coded messages can contain different
        number of newlines, and indent characters, this is preventing comparisons in
        asserts."""
        return string.replace("\n", "").replace("\t", 8 * " ")

    assert clear_rich(string1) == clear_rich(string2)
