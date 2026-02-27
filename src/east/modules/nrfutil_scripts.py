"""Generate nrfutil flash scripts and README for the east pack output.

All functions in this module are pure -- they take data and return strings. No
filesystem access is performed here (aside from reading template files); the
caller is responsible for writing the returned content to disk (typically via
WriteArtifact).

Static scripts (setup scripts, README) are stored as template files in the
``templates/`` directory next to this module. Dynamic scripts (flash, erase,
reset, recover) are generated programmatically because their content depends
on the specific batch files and device version for each build configuration.
"""

import os

from .batchfile import BatchFile

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _load_template(name: str) -> str:
    """Read a template file from the templates directory.

    Args:
        name: Filename of the template (e.g. "nrfutil_setup.sh").
    """
    path = os.path.join(_TEMPLATES_DIR, name)
    with open(path, "r") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Setup scripts
# ---------------------------------------------------------------------------


def generate_setup_script_bash() -> str:
    """Return the nrfutil_setup.sh script content.

    This script is sourced by flash.sh, erase.sh, reset.sh, and recover.sh.
    It checks that nrfutil is installed, then checks/installs the correct
    nrfutil device command version. The required version is set by the caller
    via the REQUIRED_DEVICE_VERSION variable before sourcing.
    """
    return _load_template("nrfutil_setup.sh")


def generate_setup_script_bat() -> str:
    """Return the nrfutil_setup.bat script content."""
    return _load_template("nrfutil_setup.bat")


# ---------------------------------------------------------------------------
# Flash scripts
# ---------------------------------------------------------------------------


def generate_flash_script_bash(
    batch_files: list[BatchFile], device_version: str
) -> str:
    """Generate flash.sh script content.

    Args:
        batch_files: List of BatchFile objects (with updated firmware paths and
            ext_mem_config_name set). Order is preserved from west flash --dry-run.
        device_version: Required nrfutil device command version.
    """
    lines = [
        "#!/usr/bin/env bash",
        "# Flash firmware to device using nrfutil",
        "# Usage: ./flash.sh [OPTIONS] [EXTRA_ARGS]",
        "# Options:",
        "#   --serial-number <SERIAL>  Target specific device",
        "#   --version-agnostic        Skip version checks",
        "#   EXTRA_ARGS                Any additional arguments, they will be passed to"
        "#                             nrfutil directly (e.g. --core Network)",
        "",
        "set -e",
        "",
        'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
        "",
        f'REQUIRED_DEVICE_VERSION="{device_version}"',
        "",
        "# Source common setup",
        'source "$SCRIPT_DIR/nrfutil_setup.sh"',
        'setup_nrfutil "$@"',
        'EXTRA_ARGS=$(filter_args "$@")',
        "",
        "# Change to build dir",
        'cd "$SCRIPT_DIR/.."',
        "",
    ]

    for bf in batch_files:
        # Extract domain name from batch file name (e.g., "app" from
        # "app_generated_nrfutil_batch.json")
        domain = bf.name.rsplit("_generated_nrfutil_batch.json", 1)[0]
        if domain == bf.name:
            # Fallback if naming convention doesn't match
            domain = bf.name

        lines.append(f"# Domain: {domain}")
        lines.append(f'echo "Flashing domain: {domain}"')

        cmd_parts = ["nrfutil", "device"]
        if bf.ext_mem_config_name:
            cmd_parts.extend(
                [
                    "--x-ext-mem-config-file",
                    f"{bf.ext_mem_config_name}",
                ]
            )
        cmd_parts.extend(
            [
                "x-execute-batch",
                "--batch-path",
                f"{bf.name}",
                "$EXTRA_ARGS",
            ]
        )

        lines.append(" ".join(cmd_parts))
        lines.append("")

    lines.append('echo "Flash completed successfully!"')

    return "\n".join(lines) + "\n"


def generate_flash_script_bat(batch_files: list[BatchFile], device_version: str) -> str:
    """Generate flash.bat script content.

    Args:
        batch_files: List of BatchFile objects (with updated firmware paths and
            ext_mem_config_name set). Order is preserved from west flash --dry-run.
        device_version: Required nrfutil device command version.
    """
    lines = [
        "@echo off",
        "REM Flash firmware to device using nrfutil",
        "REM Usage: flash.bat [OPTIONS]",
        "REM Options:",
        "REM   --serial-number <SERIAL>  Target specific device",
        "REM   --version-agnostic        Skip version checks",
        "REM   EXTRA_ARGS                Any additional arguments, they will be passed to"
        "REM                             nrfutil directly (e.g. --core Network)",
        "",
        "setlocal enabledelayedexpansion",
        "",
        "set SCRIPT_DIR=%~dp0",
        "",
        f"set REQUIRED_DEVICE_VERSION={device_version}",
        "",
        "REM Run common setup",
        'call "%SCRIPT_DIR%nrfutil_setup.bat" %*',
        "if %ERRORLEVEL% neq 0 exit /b 1",
        "",
        "REM Change to build dir",
        "cd %SCRIPT_DIR%..",
        "",
    ]

    for bf in batch_files:
        domain = bf.name.rsplit("_generated_nrfutil_batch.json", 1)[0]
        if domain == bf.name:
            domain = bf.name

        lines.append(f"REM Domain: {domain}")
        lines.append(f"echo Flashing domain: {domain}")

        cmd_parts = ["nrfutil", "device"]
        if bf.ext_mem_config_name:
            cmd_parts.extend(
                [
                    "--x-ext-mem-config-file",
                    f"{bf.ext_mem_config_name}",
                ]
            )
        cmd_parts.extend(
            [
                "x-execute-batch",
                "--batch-path",
                f"{bf.name}",
                "%FILTERED_ARGS%",
            ]
        )

        lines.append(" ".join(cmd_parts))
        lines.append("if %ERRORLEVEL% neq 0 (")
        lines.append(f"    echo Error: Flash failed for domain {domain}")
        lines.append("    pause")
        lines.append("    exit /b 1")
        lines.append(")")
        lines.append("")

    lines.append("echo Flash completed successfully!")
    lines.append("pause")
    lines.append("exit /b 0")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Helper scripts (erase, reset, recover)
# ---------------------------------------------------------------------------

_HELPER_SCRIPTS = [
    ("erase", "Erase device flash memory", "erase"),
    ("reset", "Reset device", "reset"),
    ("recover", "Recover device (unlock and erase)", "recover"),
]


def generate_helper_script_bash(
    name: str, description: str, command: str, device_version: str
) -> str:
    """Generate a helper bash script (erase.sh, reset.sh, or recover.sh).

    Args:
        name: Script name without extension (e.g. "erase").
        description: Human-readable description (e.g. "Erase device flash memory").
        command: The nrfutil device subcommand (e.g. "erase").
        device_version: Required nrfutil device command version.
    """
    return f"""\
#!/usr/bin/env bash
# {description}
# Usage: ./{name}.sh [--serial-number <SERIAL>] [--version-agnostic] [EXTRA_ARGS]

set -e

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"

REQUIRED_DEVICE_VERSION="{device_version}"

source "$SCRIPT_DIR/nrfutil_setup.sh"
setup_nrfutil "$@"
EXTRA_ARGS=$(filter_args "$@")

echo "{description}..."
nrfutil device {command} $EXTRA_ARGS
echo "{description.split()[0]} completed successfully!"
"""


def generate_helper_script_bat(
    name: str, description: str, command: str, device_version: str
) -> str:
    """Generate a helper Windows script (erase.bat, reset.bat, or recover.bat).

    Args:
        name: Script name without extension (e.g. "erase").
        description: Human-readable description (e.g. "Erase device flash memory").
        command: The nrfutil device subcommand (e.g. "erase").
        device_version: Required nrfutil device command version.
    """
    return f"""\
@echo off
REM {description}
REM Usage: {name}.bat [--serial-number <SERIAL>] [--version-agnostic] [EXTRA_ARGS]

setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set REQUIRED_DEVICE_VERSION={device_version}

call "%SCRIPT_DIR%nrfutil_setup.bat" %*
if %ERRORLEVEL% neq 0 exit /b 1

echo {description}...
nrfutil device {command} %FILTERED_ARGS%
if %ERRORLEVEL% neq 0 (
    echo {description} failed!
    pause
    exit /b 1
)
echo {description.split()[0]} completed successfully!
pause
exit /b 0
"""


def get_all_helper_scripts_bash(device_version: str) -> dict[str, str]:
    """Generate all helper bash scripts.

    Returns:
        Dict mapping filename (e.g. "erase.sh") to script content.
    """
    return {
        f"{name}.sh": generate_helper_script_bash(name, desc, cmd, device_version)
        for name, desc, cmd in _HELPER_SCRIPTS
    }


def get_all_helper_scripts_bat(device_version: str) -> dict[str, str]:
    """Generate all helper Windows scripts.

    Returns:
        Dict mapping filename (e.g. "erase.bat") to script content.
    """
    return {
        f"{name}.bat": generate_helper_script_bat(name, desc, cmd, device_version)
        for name, desc, cmd in _HELPER_SCRIPTS
    }


# ---------------------------------------------------------------------------
# README
# ---------------------------------------------------------------------------


def generate_readme() -> str:
    """Return README.md content for the flash package."""
    return _load_template("README.md")
