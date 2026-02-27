# Flash Artifacts

This folder contains all artifacts needed to flash the firmware to a Nordic Semiconductor device
using nrfutil.

## Requirements

1. **nrfutil** must be installed and available on your PATH.

   Download and install nrfutil from: https://www.nordicsemi.com/Products/Development-tools/nRF-Util

2. **SEGGER J-Link** software must be installed and available on your PATH.

   Download and install J-Link from: https://www.segger.com/downloads/jlink/

   **TIP**: On Windows J-Link is typically installed in `C:\Program Files (x86)\SEGGER\JLink`. You
   may need to add this directory to your PATH environment variable.

The required **nrfutil device** command will be checked and installed automatically by the scripts.

## Available Scripts

### Flash firmware

| Platform      | Command             |
| ------------- | ------------------- |
| Linux / macOS | `./linux/flash.sh`  |
| Windows       | `windows\flash.bat` |

### Erase device flash memory

| Platform      | Command             |
| ------------- | ------------------- |
| Linux / macOS | `./linux/erase.sh`  |
| Windows       | `windows\erase.bat` |

### Reset device

| Platform      | Command             |
| ------------- | ------------------- |
| Linux / macOS | `./linux/reset.sh`  |
| Windows       | `windows\reset.bat` |

### Recover device (unlock bricked device)

| Platform      | Command               |
| ------------- | --------------------- |
| Linux / macOS | `./linux/recover.sh`  |
| Windows       | `windows\recover.bat` |

## Common Options

Below options are common to all scripts.

| Option                     | Description                                                        |
| -------------------------- | ------------------------------------------------------------------ |
| `--serial-number <SERIAL>` | Target a specific device by serial number                          |
| `--version-agnostic`       | Skip version checks, use any device cmd                            |
| `EXTRA ARGS`               | Arbitrary extra arguments, they are passed to the nrfutil directly |

### Examples

```bash
# Flash firmware
./linux/flash.sh

# Flash a specific device
./linux/flash.sh --serial-number 1234567890

# Reset a specific device
./linux/reset.sh --serial-number 1234567890
```

## Running Windows scripts

To run the Windows scripts, open a Command Prompt type `cmd` in the path window of the File Explorer
and press Enter. Then run the desired script, for example:

```
windows\flash.bat
```

You can also run the scripts directly by double-clicking them in the File Explorer.

## Listing Connected Devices

To list all connected devices and their serial numbers:

```
nrfutil device list
```

## Troubleshooting

**Device not found:**

- Check USB connection
- Run `nrfutil device list` to verify the device is detected
- On Linux, you may need udev rules for USB access

**Permission denied (Linux):**

- Add udev rules for Nordic devices:
  ```
  sudo cp 99-nordic.rules /etc/udev/rules.d/
  sudo udevadm control --reload-rules
  ```
- Or run the script with sudo (not recommended)

**Device is locked/bricked:**

Example of an error message:

```
Flashing domain: hci_ipc
[00:00:00] ###### 100% [2/1 853003224] Batch failed, Failed to attach to target: The Network Error: One or more batch tasks failed:
 * 853003224: Failed to attach to target: The Network core access port is protected (All) (NotAvailableBecauseProtection)
```

- Use the recover script: `./linux/recover.sh`
- This will unlock and erase the device
- Depending on the mentioned core you might need to use `--core` option to specify the core to
  recover (e.g. `--core Network` for the above error)
