import os
import shutil

from click.testing import CliRunner

from east.__main__ import cli
from east.east_context import EastContext

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


def create_and_write(path: str, filename: str, content: str = None):
    """Create a file in the given path with the given content.

    Args:
        path (str):         Path from where to create the filename
        filename (str):     Filename can be either a direct file name such as a file.txt
                            or a longer path, such as dir_a/dir_b/file.txt
        content (str):      File content to write. If None, nothing is written.

    """
    filepath = os.path.join(path, filename)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        if content:
            f.write(content)


dummy_config = """
CONFIG_DEBUG=y
"""
dummy_cmakelists_txt = """
cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(test_project)

target_sources(app PRIVATE src/main.c)
"""


def _create_good_west_workspace(west_top_dir):
    """Main function, which will create correct west workspace. All other 'bad'
    functions will just delete from it.
    """
    folders = [
        os.path.join("project", "app"),
        os.path.join("project", "samples", "settings"),
        os.path.join("project", "samples", "dfu"),
        os.path.join("project", "tests", "basic"),
        "zephyr",
    ]

    for folder in folders:
        os.makedirs(os.path.join(west_top_dir, folder), exist_ok=True)

    create_and_write(west_top_dir, ".west/config", west_config_content)
    create_and_write(west_top_dir, "project/west.yml", nrfsdk_yaml_content)
    create_and_write(west_top_dir, "project/east.yml", east_yaml_single_app)
    create_and_write(
        west_top_dir, "project/app/conf/nrf52840dk_nrf52840.conf", dummy_config
    )
    create_and_write(west_top_dir, "project/app/CMakeLists.txt", dummy_cmakelists_txt)

    # Board files, just create them, you do not need to write anything.
    board_path = "project/boards/arm/custom_nrf52840dk"
    board_files = [
        "board.cmake",
        "Kconfig",
        "Kconfig.board",
        "Kconfig.defconfig",
        "revision.cmake",
        "custom_nrf52840dk - pinctrl.dtsi",
        "custom_nrf52840dk.dts",
        "custom_nrf52840dk.yaml",
        "custom_nrf52840dk_1_0_0.conf",
        "custom_nrf52840dk_1_0_0.overlay",
        "custom_nrf52840dk_1_1_0.conf",
        "custom_nrf52840dk_1_1_0.overlay",
        "custom_nrf52840dk_2_20_1.conf",
        "custom_nrf52840dk_2_20_1.overlay",
        "custom_nrf52840dk_defconfig",
    ]
    for board_file in board_files:
        create_and_write(west_top_dir, os.path.join(board_path, board_file))
    board_path = "project/boards/arm/nrf52840dk_nrf52840"
    board_files = [
        "board.cmake",
        "Kconfig",
        "Kconfig.board",
        "Kconfig.defconfig",
        "revision.cmake",
        "nrf52840dk_nrf52840.dts",
        "nrf52840dk_nrf52840.yaml",
        "nrf52840dk_nrf52840_defconfig",
    ]
    for board_file in board_files:
        create_and_write(west_top_dir, os.path.join(board_path, board_file))

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
    """Creates a correct west workspace in west_top_dir, with multi app east yaml.

    Args:
        west_top_dir (str): Path to west top dir.

    Returns:
        Path to the project inside west top dir.
    """
    create_and_write(west_top_dir, "project/east.yml", east_yaml_multiple_apps)

    # We need this to clean any files left by create_good_west
    shutil.rmtree(os.path.join(west_top_dir, "project/app"))
    os.makedirs(os.path.join(west_top_dir, "project/app/test_one"), exist_ok=True)
    os.makedirs(os.path.join(west_top_dir, "project/app/test_two"), exist_ok=True)
    create_and_write(
        west_top_dir, "project/app/test_one/conf/nrf52840dk_nrf52840.conf", dummy_config
    )


def west_no_nrf_sdk_in_yaml(west_top_dir):
    """Creates a west workspace without nrf-sdk in west.yaml.

    Args:
        west_top_dir (): Path to west top dir.
    """
    create_and_write(west_top_dir, ".west/config", west_config_content)
    create_and_write(west_top_dir, "project/west.yml", zephyrsdk_yaml_content)


def assert_strings_equal(string1: str, string2: str):
    """Helper that should be used when comparing strings that come from east's stdout
    and east's internal hardcoded strings.

    Returns:
        Asserts if strings are different
    """

    def clear_rich(string):
        """Output from runner.invoke and hard-coded messages can contain different
        number of newlines, and indent characters, this is preventing comparisons in
        asserts.
        """
        return string.replace("\n", "").replace("\t", 8 * " ")

    assert clear_rich(string1) == clear_rich(string2)


def helper_test_against_west_run(
    monkeypatch,
    mocker,
    path,
    east_cmd,
    expected_west_cmd=None,
    expected_west_cmds=None,
    should_succed=True,
):
    """Helper function for making tests easier to read.

    Args:
        monkeypatch ():         fixture
        mocker ():              fixture
        path ():                To which path should we change
        east_cmd ():            which east command should be called
        expected_west_cmd ():   A single expected west cmd, a string.
        expected_west_cmds ():  A List of expected west_cmds.
        should_succed ():       If true then the command should succeded.

    Only a expected_west_cmd or expected_west_cmds can be given, both not both.
    If none is given then no run_west call should happend.

    Returns:
        Result object, which can be further checked.
    """
    runner = CliRunner()

    # Mock output of git commmand, so tests do not have to depend on it
    mocker.patch(
        "east.workspace_commands.release_commands.get_git_version",
        return_value={"tag": "v1.0.0.", "hash": ""},
    )
    mocker.patch(
        "east.workspace_commands.codechecker_helpers.get_git_version",
        return_value={"tag": "v1.0.0.", "hash": ""},
    )

    monkeypatch.chdir(path)
    mocker.patch(
        "east.east_context.EastContext.run_west",
        return_value={"output": "", "returncode": 0},
    )

    # Setting catch_exceptions to False enables us to see programming errors in East
    # code
    result = runner.invoke(cli, east_cmd.strip().split(" "), catch_exceptions=False)

    run_west = EastContext.run_west

    if expected_west_cmds:
        # This conversion is needed due to assert_has_calls interface
        calls = [
            mocker.call(cmd, exit_on_error=False, silent=True, return_output=True)
            for cmd in expected_west_cmds
        ]
        run_west.assert_has_calls(calls)

    elif expected_west_cmd:
        run_west.assert_called_once_with(expected_west_cmd)
    else:
        run_west.assert_not_called()

    expected_return_code = 0 if should_succed else 1

    assert result.exit_code == expected_return_code
    return result


def helper_test_against_west_dbg(
    monkeypatch,
    mocker,
    path,
    east_cmd,
    expected_west_cmd=None,
    expected_west_cmds=None,
    should_succed=True,
):
    """Helper function for tests easier to debug.

    Running this instead of the real helper will just make sure that the correct command
    runs, but it will not execute any east.run_west() calls.

    Args:
        monkeypatch ():         fixture
        mocker ():              fixture
        path ():                To which path should we change
        east_cmd ():            which east command should be called
        expected_west_cmd ():   Not used
        expected_west_cmds ():  Not used
        should_succed ():       Not used
    """
    _ = expected_west_cmd
    _ = expected_west_cmds
    _ = should_succed

    runner = CliRunner()

    # Mock output of git commmand, so tests do not have to depend on it
    mocker.patch(
        "east.workspace_commands.release_commands.get_git_version",
        return_value={"tag": "v1.0.0.", "hash": ""},
    )

    monkeypatch.chdir(path)
    mocker.patch("east.east_context.EastContext.run_west")

    result = runner.invoke(cli, east_cmd.strip().split(" "))
    print(result.output)
