import os
import re
from typing import List

from ..helper_functions import return_dict_on_match


def is_child_in_parent(parent, child):
    """Check if the child path is in parent path
        parent (): path
        child ():  path
    Returns: True if yes, otherwise False.
    """

    # Smooth out relative path names, note: if you are concerned about symbolic
    # links, you should use os.path.realpath too
    parent = os.path.abspath(parent)
    child = os.path.abspath(child)

    # Compare the common path of the parent and child path with the common path of
    # just the parent path. Using the commonpath method on just the parent path will
    # regularise the path name in the same way as the comparison that deals with
    # both paths, removing any trailing path separator
    return os.path.commonpath([parent]) == os.path.commonpath([parent, child])


def _construct_required_cmake_args(
    conf_files: List[str], board: str, path_prefix: str, source_dir: str
) -> str:
    """
    Constructs required cmake args from conf_files. Adds board specific conf file if it
    is found.
    Path prefix is applied, for cases where sample inherits a list conf_files.

        conf_files (List(str)):     List of conf files
        board (str):                West board name
        path_prefix (str):          Path prefix added to conf files

    Returns:
        Cmake args
    """
    # Determine if there is some prefix involved
    prefix = f"{path_prefix}/" if path_prefix else ""
    # We always use common.conf
    cmake_args = f"-DCONF_FILE={prefix}conf/common.conf"

    overlay_configs = []

    # If a west board is given search for board specific config file and add it to the
    # start of overlay_configs, if it is found.
    if board:
        # Sanitize the board input, user might gave hv version
        board = board.split("@")[0]

        # Location of the board file depends on the source_dir and prefix
        board_prefix = f"{source_dir}/{prefix}" if source_dir else f"{prefix}"
        board_conf = f"{board_prefix}conf/{board}.conf"

        if os.path.isfile(board_conf):
            overlay_configs.append(f"{board}.conf")

    # Then add conf_files if there are any
    overlay_configs += conf_files

    # Glue together configs
    if len(overlay_configs) > 0:
        overlay_config = ";".join([f"{prefix}conf/{file}" for file in overlay_configs])
        cmake_args += f' -DOVERLAY_CONFIG="{overlay_config}"'

    return f"{cmake_args}"


def _construct_previous_cmake_args(build_dir: str) -> str:
    """
    Constructs previous cmake args by extracting them from the build file that was
    created in the previous build.

        build_dir (str):    Location of the build directory.

    Returns:
        Cmake args
    """
    build_location = build_dir.strip("/") if build_dir else "build"
    build_file = f"{build_location}/image_preload.cmake"

    try:
        with open(build_file, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        # Just return empty string in this case, this will trigger rebuild in any case.
        return ""

    def extract(pattern, content):
        """
        Performs specific extract from content, based on pattern. If pattern is not
        found None is returned.
        """
        hit = re.search(pattern, content)
        return hit.group().split(" ")[1].replace('"', "") if hit else None

    # This hit should always be found, I do not know in what case it is not.
    conf_file = extract(".*CACHED_CONF_FILE.*", content)
    cmake_args = f"-DCONF_FILE={conf_file}"

    overlay_config = extract(".*OVERLAY_CONFIG.*", content)
    if overlay_config:
        cmake_args += f' -DOVERLAY_CONFIG="{overlay_config}"'

    return cmake_args


build_type_misuse_no_east_yml_msg = """
[bold yellow]east.yml[/] not found in project's root directory, option [bold
cyan]-/u--build-type[/] needs it to determine [bold]Kconfig[/] overlay files, exiting!"""

build_type_misuse_msg = """
Option [bold cyan]--build-type[/] can only be used inside of the application folder, exiting!"""

build_type_misuse_no_app_msg = """
Option [bold cyan]--build-type[/] can only be used when apps key in [bold yellow]east.yml[/] has at least one
application entry!"""


def no_build_type_msg(build_type):
    return (
        f"\nGiven --build-type [bold]{build_type}[/] does [bold red]not"
        " exist[/] for this app!"
    )


def construct_extra_cmake_arguments(east, build_type, board, build_dir, source_dir):
    """Construct extra cmake arguments for west build command.

    This function will construct cmake_arguments (specifically values for OVERLAY_CONFIG
    and CONF_FILE defines), based on:
    * given build type
    * given board
    * contents of east.yml file
    * contents of build folder if found

    The function behaviour is described:
    * in docs/configuration.md document - That document basically describes how should
    east build behave.
    * in tests/test_build_type.py - Tests the behaviour east build command in a
    variety of different scenarios.

        east ():            East context
        build_type ():      Build type given from the east build
        board ():           Board given from the east build
        build_dir ():       Location of build_dir, if None then "./build" is used

    Returns:  Tuple of strings
                First string are extra cmake arguments for west build command should be
                placed after `--` in west command
                Second string is diagnostic message that can be printed. It might not be
                given so it should be checked first.
    """

    if not east.east_yml:
        if not build_type:
            # east.yml is optional, if it is not present present then default to plain
            # west behaviour: no cmake args
            return ("", "")
        else:
            east.print(build_type_misuse_no_east_yml_msg)
            east.exit()

    # Modify current working dir, if source_dir is used, rstrip is needed cause
    # path.join adds one "/" if joining empty string.
    source_dir = source_dir if source_dir else ""
    cwd = os.path.join(east.cwd, source_dir).rstrip("/")

    # Does the relative path contain app or samples string
    relpath = os.path.relpath(cwd, start=east.project_dir)
    inside_app = "app" in relpath
    inside_sample = "samples" in relpath

    if not inside_app:
        if build_type:
            # --build-type can only be given from inside of the project dir
            # (--source-dir can be given to point to some app), or directly inside app.
            # Any other location is not allowed.
            east.print(build_type_misuse_msg)
            east.exit()
        if not build_type and not inside_sample:
            # We are not inside app and not inside sample, no build type was given, we
            # are default to plain west behaviour: no cmake args.
            return ("", "")

    # We get past this point if we are inside app or sample.

    # apps field is optional, using build type without that field is however not
    # allowed.
    app_array = east.east_yml.get("apps")
    if build_type and not app_array:
        east.print(build_type_misuse_no_app_msg)
        east.exit()

    # If inside samples determine in which sample are we, get its element
    if inside_sample:
        # samples key is optional, if it is not present in east_yml then we default to
        # plain west behaviour: no cmake args
        sample_array = east.east_yml.get("samples")
        if not sample_array:
            return ("", "")

        sample_name = os.path.basename(cwd)
        sample_dict = return_dict_on_match(sample_array, "name", sample_name)

        if not sample_dict or "inherit-build-type" not in sample_dict:
            # In case where there is no inherit, or sample is not listed we default to
            # plain west behavior: no cmake args.
            return ("", "")

        # Determine if we have to inherit from some app or we can just use prj.conf
        inherited_app = sample_dict["inherit-build-type"]["app"]
        build_type = sample_dict["inherit-build-type"]["build-type"]
        app = return_dict_on_match(app_array, "name", inherited_app)
        path_to_project_dir = os.path.relpath(east.project_dir, start=cwd)

        if len(app_array) == 1:
            path_prefix = os.path.join(path_to_project_dir, "app")
        else:
            path_prefix = os.path.join(path_to_project_dir, "app", inherited_app)

    if inside_app:
        # If we do not have an app array and we there is no build type, we default to
        # plaing west behaviour: no cmake args.
        if not app_array:
            return ("", "")

        # Determine what kind of project it is, single or multi app
        if len(app_array) == 1:
            app = app_array[0]
        else:
            # Get the folder name that we are in
            app = return_dict_on_match(app_array, "name", os.path.basename(cwd))
        path_prefix = ""

    # "release" is a special, implicit, default, build type. Samples can request to
    # inherit from it, in that case only the common.conf is added to the build.
    if build_type == "release":
        build_type = None

    # Extract a list of conf files from the app, exit if they do not exist.
    conf_files = []
    if build_type:
        matched_type = return_dict_on_match(app["build-types"], "type", build_type)
        if not matched_type:
            east.print(no_build_type_msg(build_type))
            east.exit()

        conf_files = matched_type["conf-files"]

    # Construct required cmake args,
    required_cmake_args = _construct_required_cmake_args(
        conf_files, board, path_prefix, source_dir
    )

    # If build file exists then construct previous cmake_args
    previous_cmake_args = _construct_previous_cmake_args(build_dir)

    if required_cmake_args == previous_cmake_args:
        return ("", "")
    else:
        if previous_cmake_args:
            msg = (
                "[italic bold dim]💬 Old settings found in build folder, forcing CMake"
                " rebuild[/]"
            )
        else:
            # Previous cmake args are empty string, no build folder was found
            msg = "[italic bold dim]💬 Build folder not found, running CMake build[/]"
        return required_cmake_args, msg
