#!/usr/bin/env bash
# Common setup script for nrfutil flash operations
# This script is sourced by flash.sh, erase.sh, reset.sh, and recover.sh
#
# Required variables (set before sourcing):
#   REQUIRED_DEVICE_VERSION  - Required device command version
#
# Optional variables:
#   VERSION_AGNOSTIC - If set to "1", skip version checks and use latest device command

set -e

# Parse --version-agnostic flag from arguments
parse_version_agnostic() {
    for arg in "$@"; do
        if [ "$arg" = "--version-agnostic" ]; then
            VERSION_AGNOSTIC=1
            return
        fi
    done
}

# Check if nrfutil is installed
check_nrfutil_installed() {
    if ! command -v nrfutil &>/dev/null; then
        echo "Error: nrfutil is not installed or not found on PATH."
        echo ""
        echo "nrfutil is required to flash firmware to the device."
        echo ""
        echo "Download and install nrfutil from:"
        echo "  https://www.nordicsemi.com/Products/Development-tools/nRF-Util"
        echo ""
        echo "After downloading, make sure the nrfutil binary is on your PATH."
        exit 1
    fi
    echo "nrfutil found: $(command -v nrfutil)"
}

# Check if JLinkExe is installed
check_jlink_installed() {
    if ! command -v JLinkExe &>/dev/null; then
        echo "Error: JLinkExe is not installed or not found on PATH."
        echo ""
        echo "SEGGER J-Link software is required for communicating with the device."
        echo ""
        echo "Download and install J-Link from:"
        echo "  https://www.segger.com/downloads/jlink/"
        echo ""
        echo "After installing, make sure JLinkExe is on your PATH."
        exit 1
    fi
    echo "JLinkExe found: $(command -v JLinkExe)"
}

# Get installed device command version
get_device_version() {
    # Use awk only to avoid grep exit code 1 when no match (causes issues with set -e)
    nrfutil list 2>/dev/null | awk '/^device/ {print $2}'
}

# Prompt user for confirmation
confirm_action() {
    local prompt="$1"
    echo ""
    echo "$prompt"
    read -p "Do you want to proceed? [y/N]: " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted by user."
        exit 1
    fi
}

# Check and install device command (exact version match required)
check_device_command() {
    local installed_version
    installed_version=$(get_device_version)

    if [ "$VERSION_AGNOSTIC" = "1" ]; then
        if [ -z "$installed_version" ]; then
            echo "nrfutil device command not installed."
            confirm_action "The device command needs to be installed (latest version)."
            echo "Installing latest device command..."
            if ! nrfutil install device; then
                echo "Error: Failed to install device command."
                exit 1
            fi
            echo "Device command installed successfully."
        else
            echo "Version-agnostic mode: device command version $installed_version (any version accepted)"
        fi
        return
    fi

    # Strict version checking mode
    if [ -z "$installed_version" ]; then
        echo "nrfutil device command not installed."
        confirm_action "The device command version $REQUIRED_DEVICE_VERSION needs to be installed."
        echo "Installing device command version $REQUIRED_DEVICE_VERSION..."
        if ! nrfutil install device="$REQUIRED_DEVICE_VERSION"; then
            echo "Error: Failed to install device command."
            exit 1
        fi
        echo "Device command installed successfully."
        return
    fi

    if [ "$installed_version" != "$REQUIRED_DEVICE_VERSION" ]; then
        echo "Device command version mismatch"
        echo "  Installed: $installed_version"
        echo "  Required:  $REQUIRED_DEVICE_VERSION"
        confirm_action "The device command needs to be updated to version $REQUIRED_DEVICE_VERSION."
        echo "Installing device command version $REQUIRED_DEVICE_VERSION (forcing update)..."
        if ! nrfutil install device="$REQUIRED_DEVICE_VERSION" --force; then
            echo "Error: Failed to install device command."
            exit 1
        fi
        echo "Device command updated successfully."
        return
    fi

    echo "Device command version: $installed_version (OK)"
}

# Main setup function - call this from flash scripts
setup_nrfutil() {
    parse_version_agnostic "$@"
    check_nrfutil_installed
    check_jlink_installed
    check_device_command
    echo ""
}

# Remove --version-agnostic from arguments (for passing to nrfutil)
filter_args() {
    local filtered=""
    for arg in "$@"; do
        if [ "$arg" != "--version-agnostic" ]; then
            filtered="$filtered $arg"
        fi
    done
    echo "$filtered"
}
