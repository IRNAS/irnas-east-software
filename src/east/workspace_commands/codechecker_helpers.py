import glob
import os
import plistlib as plist
import re


def check_for_build_folder(east):
    """Check that build dir exists."""

    if not os.path.isdir("build"):
        east.print(
            "\nFolder [magenta bold italic]build[/] was [bold red]not found[/] in current working directory.\n\n"
            "Build your project first and rerun this command."
        )
        east.exit()


def check_for_compile_commands_json(east, compile_commands):
    """Check that compile_commands.json exists in the build dir."""

    if not os.path.exists(compile_commands):
        east.print(
            "\nFile [cyan bold]build/compile_commands.json[/] was [bold red]not found[/].\n"
            "Check if your project's [cyan bold]CMakelists.txt[/] file contains the below line:\n\n"
            "[bold]set(CMAKE_EXPORT_COMPILE_COMMANDS ON)[/]\n"
        )
        east.exit()


def check_for_codechecker_config_yaml(east, cfg):
    """Check that codechecker_config.yaml exists in the project's root dir."""

    if not os.path.exists(cfg):
        east.print(
            "\nFile [cyan bold]codechecker_config.yaml[/] was [bold red]not found[/] in project's git root dir.\n"
            "CodeChecker requires this file to function normally.\n\n"
            "Run below command to see an example of a config: \n\n"
            "\t[cyan bold]east codechecker example-config\n"
        )
        east.exit()


def ineffective_log_macro_found(diag):
    """Returns true if clang-tidy diagnostic is about ineffective bitwise and operation
    in a LOG_* macro.

    Production source code is full of those, and they are not really useful to see in
    the reports. This function is used to filter them out.
    """

    desc = "ineffective bitwise and operation"

    if diag["description"] == desc:
        for path in diag["path"]:
            if "message" in path:
                hit = re.search("expanded from macro '.*LOG_.*'", path["message"])
                if hit:
                    return True
    return False


def conditional_operator_in_macro_found(diag):
    """Returns true if clang-tidy diagnostic is about conditional operator in a
    SHELL_CMD_* macro.
    """

    desc = "conditional operator with identical true and false expressions"

    if diag["description"] == desc:
        for path in diag["path"]:
            if "message" in path:
                patterns = [
                    "expanded from macro 'SHELL_CMD_.*'",
                    "expanded from macro 'APP_EVENT_TYPE_DEFINE'",
                ]

                for pattern in patterns:
                    if re.search(pattern, path["message"]):
                        return True
    return False


def var_never_read_before_disabled_macro_found(files, diag):
    """Returns true if clang-tidy diagnostic is about value being stored to a variable,
    and not being read, but this variable is later passed into some kind of a disabled
    macro, such as __ASSERT* or LOG_* macro.
    """

    # Determine first if the description of the diagnostic is as expected for this case
    desc_regexes = [
        "Value stored to '(.*)' during its initialization is never read",
        "Value stored to '(.*)' is never read",
    ]

    for desc_regex in desc_regexes:
        hit = re.search(desc_regex, diag["description"])
        if hit:
            # Extracted variable name
            var = hit.group(1)
            break

    if not hit:
        return False

    # A hit was found, locate the file where the diagnostic was found
    file = files[diag["location"]["file"]]

    # Open it and start reading from the line where the diagnostic was found
    with open(file, "r") as f:
        for _ in range(diag["location"]["line"]):
            next(f)

        for line in f:
            # If you hit a line where variable is passed to __ASSERT* or LOG_* macro,
            # then this is a false positive, and should be removed
            patterns = [
                f".*__ASSERT.*\(.*{var}.*,.*",
                f".*LOG_.*\(.*,.*{var}.*",
            ]

            for pattern in patterns:
                if re.search(pattern, line):
                    return True

            # If you hit a line that uses the variable in any way, then this is a true
            # positive
            if re.search(f".*{var}.*", line):
                return False


def cleanup_plist_files(east, output):
    """Cleanup generated plist files by removing diagnostics that are not useful."""

    # Conveniance variable, as the listeral is quite long
    hash = "issue_hash_content_of_line_in_context"

    for file in glob.glob(os.path.join(output, "*.plist")):

        with open(file, "rb") as f:
            data = plist.load(f)

        diags = data["diagnostics"]

        diags_for_removal = []

        # Iterate through all diagnostics in the plist file and filter ones that you do
        # not want.
        # You can place any custom logic below to filter out diagnostics that you
        # do not want.
        for diag in diags:
            if (
                conditional_operator_in_macro_found(diag)
                or ineffective_log_macro_found(diag)
                or var_never_read_before_disabled_macro_found(data["files"], diag)
            ):

                diags_for_removal.append(diag[hash])

        # Removal happens here
        data["diagnostics"] = [
            diag for diag in diags if diag[hash] not in diags_for_removal
        ]

        # Write the plist file back
        with open(file, "wb") as f:
            plist.dump(data, f)


def create_skip_file(east, output):
    """Create skip file for CodeChecker.

    Generated skip file skips analysis of Zephyr, NCS, external repositories and
    contents of any build folder inside the project's root dir.

    We are skipping build folder because it contains generated .c files that are not in
    other folders.
    """

    skip_file = os.path.join(output, "skip_file.txt")

    os.makedirs(output, exist_ok=True)

    if not os.path.exists(skip_file):
        with open(skip_file, "w") as f:
            f.write(f"-{east.project_dir}/*/build/*\n")
            f.write(f"+{east.project_dir}/*\n")
            f.write(f"-{east.west_dir_path}/*\n ")

    return skip_file
