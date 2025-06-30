import os
from typing import NamedTuple, Sequence

from ..constants import EAST_GITHUB_URL


def tsuite_determine_path(board: str, name: str, toolchain: str | None) -> str:
    """Determine the path to the testsuite's build directory.

    Args:
        board (str): Normalized board name,
        name (str): The testsuite name as it appears in twister.json,
        toolchain (str): The toolchain used for this testsuite, as it appears in twister.json.

    Returns:
        str: The path to the testsuite's build directory.
    """
    # if the version is v4.0.0 or later, the paths used are different
    # from v3.x versions, so we need to adjust the paths accordingly.
    if toolchain:
        return os.path.join(board, toolchain, name)
    else:
        return os.path.join(board, name)


class TSuite(NamedTuple):
    """TSuite object that represents a single testsuite in twister.json.

    The class name was intentionally shortened to TSuite to avoid pytest's automatic
    test discovery.
    """

    # Name of the testsuite, e.g., app.prod, samples.blinky
    name: str
    # Normalized board name, e.g., nrf52840dk_nrf52840 or nrf52840dk@1.0.0_nrf52840
    board: str
    # Raw board name from twister.json, e.g., nrf52840dk/nrf52840
    raw_board: str
    # Path to the project where the testsuite is located.
    path: str
    # Path to the testsuite's build directory inside the twister_out directory.
    twister_out_path: str
    # Status of the testsuite, e.g., passed, failed, skipped
    status: str
    # Is the testsuite runnable or not
    runnable: bool

    # The "toolchain" used to build the testsuite. For Zephyr v3, this will not exist.
    # See commit by Anas: https://github.com/zephyrproject-rtos/zephyr/commit/11e656bb6a38614b663383a40e044c4941d0c841#diff-0a0df38c6d70056ac2d7f06a7a16f8a148d1013d87fae6222d6a64323b6702cb
    toolchain: str | None

    @classmethod
    def list_from_twister_json(cls, twister_json: dict) -> Sequence["TSuite"]:
        """Create a list of TSuite objects from a list of testsuites from twister.json."""
        if "testsuites" not in twister_json:
            msg = (
                f"<twister_out>/twister.json is missing the 'testsuites' key.\n\n"
                "This shouldn't happen. Please report this "
                f"to East's bug tracker on {EAST_GITHUB_URL}."
            )
            raise Exception(msg)

        # WARN: All accessed fields should be checked for existence.
        required_keys = set(["name", "platform", "run_id", "status", "runnable"])

        # Error due to missing required keys is not expected to happen often, so
        # we error out immediately, if it happens.
        # Error due to the failed runs is expected to happen more often, so we
        # first process all testsuites, determine if there are any failed runs and
        # then error out if needed.
        def create_tsuite(d: dict):
            """Create a single TSuite object from a dictionary."""
            if not required_keys.issubset(d.keys()):
                msg = (
                    f"The following testsuite json: \n\n{d}\n\n in "
                    f"<twister_out>/twister.json is missing one or more of the "
                    "following keys: {required_keys}.\n\n"
                    "This shouldn't happen. Please report this to East's bug tracker "
                    f"on {EAST_GITHUB_URL}."
                )
                raise Exception(msg)

            board = d["platform"].replace("/", "_")
            name = os.path.basename(d["name"])
            toolchain = d.get("toolchain", None)

            return cls(
                name,
                board=board,
                raw_board=d["platform"],
                path=os.path.dirname(d["name"]),
                twister_out_path=tsuite_determine_path(board, d["name"], toolchain),
                status=d["status"],
                runnable=d["runnable"],
                toolchain=toolchain,
            )

        return [
            create_tsuite(ts)
            for ts in twister_json["testsuites"]
            if ts.get("status", "") != "filtered"
        ]

    def did_fail(self) -> bool:
        """Check if the testsuite failed."""
        return self.status == "failed"

    def did_build(self) -> bool:
        """Check if the testsuite was built."""
        # either status is "passed",
        # or status is "not run" and "runnable" is False
        #
        # Both are possible since there was a change in this logic in Zephyr 4.0
        # See:
        # https://github.com/zephyrproject-rtos/zephyr/blob/v4.0.0/scripts/pylib/twister/twisterlib/runner.py#L555
        # https://github.com/zephyrproject-rtos/zephyr/blob/v3.7.1/scripts/pylib/twister/twisterlib/runner.py#L287
        return self.status == "passed" or (
            self.status == "not run" and not self.runnable
        )
