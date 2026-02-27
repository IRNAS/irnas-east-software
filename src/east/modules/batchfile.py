import json
import os
from typing import NamedTuple


class BatchFile(NamedTuple):
    """BatchFile object that represents a batch file with its content and path."""

    content: str
    name: str
    # Name of the associated ext-mem-config file, if any. Set during dry-run parsing.
    ext_mem_config_name: str | None = None

    @classmethod
    def from_path(cls, path: str, ext_mem_config_name: str | None = None) -> "BatchFile":
        """Create a BatchFile object by reading the content from the given path.

        Args:
            path: Path to the batch JSON file.
            ext_mem_config_name: Name of the associated ext-mem-config file, if any.
        """
        with open(path, "r") as f:
            content = f.read()

        file_name = path.split(os.path.sep)[-1]
        app_name = path.split(os.path.sep)[-3]

        return cls(content, f"{app_name}_{file_name}", ext_mem_config_name)

    def get_fw_files(self) -> list[str]:
        """Extract firmware file paths from a batch JSON file.

        Returns:
            List of paths to firmware files referenced in the batch file.
        """
        batch_data = json.loads(self.content)

        fw_files = []

        for op in batch_data["operations"]:
            if "firmware" in op["operation"]:
                fw_files.append(op["operation"]["firmware"]["file"])

        return fw_files

    def get_device_version(self) -> str | None:
        """Extract the nrfutil_device_version from the batch file content.

        Returns:
            The device version string, or None if not present.
        """
        batch_data = json.loads(self.content)
        return batch_data.get("nrfutil_device_version")

    def update_matching_fw_file(self, old_path: str, new_path: str) -> "BatchFile":
        """Return a new BatchFile object with the firmware file path updated.

        Args:
            old_path: The old firmware file path to be replaced. Doesn't have to be an
            exact match, just needs to be a substring of the path in the batch file.
            new_path: The new firmware file path to replace with.

        Returns:
            A new BatchFile object with the updated firmware file path.
        """
        batch_data = json.loads(self.content)

        for op in batch_data["operations"]:
            if "firmware" in op["operation"]:
                if old_path in op["operation"]["firmware"]["file"]:
                    op["operation"]["firmware"]["file"] = new_path

        new_content = json.dumps(batch_data, indent=2)
        return BatchFile(new_content, self.name, self.ext_mem_config_name)
