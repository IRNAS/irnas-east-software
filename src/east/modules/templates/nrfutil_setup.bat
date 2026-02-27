@echo off
REM Common setup script for nrfutil flash operations
REM This script is called by flash.bat, erase.bat, reset.bat, and recover.bat
REM
REM Required environment variables (set before calling):
REM   REQUIRED_DEVICE_VERSION  - Required device command version
REM
REM Sets:
REM   SETUP_OK - Set to 1 if setup succeeded
REM   VERSION_AGNOSTIC - Set to 1 if --version-agnostic flag was passed
REM   FILTERED_ARGS - Arguments with --version-agnostic removed

setlocal enabledelayedexpansion

set SETUP_OK=0
REM Preserve VERSION_AGNOSTIC if already set by caller, otherwise default to 0
if not defined VERSION_AGNOSTIC set VERSION_AGNOSTIC=0
set FILTERED_ARGS=

REM Parse arguments for --version-agnostic
for %%a in (%*) do (
    if "%%a"=="--version-agnostic" (
        set VERSION_AGNOSTIC=1
    ) else (
        set FILTERED_ARGS=!FILTERED_ARGS! %%a
    )
)

REM Check if nrfutil is installed
where nrfutil >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: nrfutil is not installed or not found on PATH.
    echo.
    echo nrfutil is required to flash firmware to the device.
    echo.
    echo Download and install nrfutil from:
    echo   https://www.nordicsemi.com/Products/Development-tools/nRF-Util
    echo.
    echo After downloading, make sure the nrfutil binary is on your PATH.
    pause
    exit /b 1
)
echo nrfutil found on PATH.

REM Check if JLink is installed
where JLink >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: JLink is not installed or not found on PATH.
    echo.
    echo SEGGER J-Link software is required for communicating with the device.
    echo.
    echo Download and install J-Link from:
    echo   https://www.segger.com/downloads/jlink/
    echo.
    echo After installing, make sure JLink is on your PATH.
    pause
    exit /b 1
)
echo JLink found on PATH.

if "%VERSION_AGNOSTIC%"=="1" (
    echo Version-agnostic mode: skipping device version check
    goto :check_device
)

:check_device
REM Check if device command is installed
nrfutil device --help >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo nrfutil device command not installed.
    goto :install_device_prompt
)

REM Get device version
for /f "tokens=2" %%v in ('nrfutil list 2^>^&1 ^| findstr /r "^device"') do (
    set INSTALLED_DEVICE_VERSION=%%v
)

if "%VERSION_AGNOSTIC%"=="1" (
    echo Version-agnostic mode: device command version %INSTALLED_DEVICE_VERSION% ^(any version accepted^)
    goto :setup_done
)

REM Check device version (exact match required)
if not "%INSTALLED_DEVICE_VERSION%"=="%REQUIRED_DEVICE_VERSION%" (
    echo Device command version mismatch
    echo   Installed: %INSTALLED_DEVICE_VERSION%
    echo   Required:  %REQUIRED_DEVICE_VERSION%
    goto :update_device_prompt
)

echo Device command version: %INSTALLED_DEVICE_VERSION% ^(OK^)
goto :setup_done

:install_device_prompt
echo.
if "%VERSION_AGNOSTIC%"=="1" (
    echo The device command needs to be installed ^(latest version^).
) else (
    echo The device command version %REQUIRED_DEVICE_VERSION% needs to be installed.
)
set /p CONFIRM="Do you want to proceed? [y/N]: "
if /i not "%CONFIRM%"=="y" (
    echo Aborted by user.
    exit /b 1
)
if "%VERSION_AGNOSTIC%"=="1" (
    echo Installing latest device command...
    nrfutil install device
) else (
    echo Installing device command version %REQUIRED_DEVICE_VERSION%...
    nrfutil install device=%REQUIRED_DEVICE_VERSION%
)
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to install device command.
    exit /b 1
)
echo Device command installed successfully.
goto :setup_done

:update_device_prompt
echo.
echo The device command needs to be updated to version %REQUIRED_DEVICE_VERSION%.
set /p CONFIRM="Do you want to proceed? [y/N]: "
if /i not "%CONFIRM%"=="y" (
    echo Aborted by user.
    exit /b 1
)
echo Installing device command version %REQUIRED_DEVICE_VERSION% ^(forcing update^)...
nrfutil install device=%REQUIRED_DEVICE_VERSION% --force
if %ERRORLEVEL% neq 0 (
    echo Error: Failed to install device command.
    pause
    exit /b 1
)
echo Device command updated successfully.

:setup_done
echo.
set SETUP_OK=1
endlocal & set SETUP_OK=%SETUP_OK% & set VERSION_AGNOSTIC=%VERSION_AGNOSTIC% & set FILTERED_ARGS=%FILTERED_ARGS%
exit /b 0
