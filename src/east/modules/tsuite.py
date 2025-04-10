import os
from typing import NamedTuple, Sequence

from ..constants import EAST_GITHUB_URL


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
        required_keys = set(["name", "platform", "run_id", "status"])

        # Error due to missing required keys is not expected to happend often, so
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

            return cls(
                name,
                board=board,
                raw_board=d["platform"],
                path=os.path.dirname(d["name"]),
                twister_out_path=os.path.join(board, d["name"]),
                status=d["status"],
            )

        return [create_tsuite(ts) for ts in twister_json["testsuites"]]

    def did_fail(self) -> bool:
        """Check if the testsuite failed."""
        return self.status != "passed"
