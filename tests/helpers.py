import os
import shutil
from contextlib import contextmanager

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


def _create_and_write(path: str, filename: str, content: str):
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


def _create_good_west_workspace(west_top_dir):
    """
    Main function, which will create correct west workspace. All other 'bad'
    functions will just delete from it.
    """
    _create_and_write(west_top_dir, ".west/config", west_config_content)
    _create_and_write(west_top_dir, "project/west.yml", nrfsdk_yaml_content)
    return os.path.join(west_top_dir, "project")


def create_good_west(west_top_dir):
    """Creates a correct west workspace in west_top_dir.

    Args:
        west_top_dir (str): Path to west top dir.

    Returns:
        Path to the project inside west top dir.
    """
    return _create_good_west_workspace(west_top_dir)


def west_no_nrf_sdk_in_yaml(west_top_dir):
    """Creates a west workspace without nrf-sdk in west.yaml

    Args:
        west_top_dir (): Path to west top dir.
    """
    _create_and_write(west_top_dir, ".west/config", west_config_content)
    _create_and_write(west_top_dir, "project/west.yml", zephyrsdk_yaml_content)
