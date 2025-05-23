import copy
import os

import pytest

from east.modules.tsuite import TSuite

test_suite_json = {
    "testsuites": [
        {
            "name": "app/app.prod",
            "arch": "arm",
            "platform": "custom_board@1.0.0/nrf52840",
            "path": "../project/app",
            "run_id": "953b256c22f70c8293b9b625baea26ee",
            "runnable": False,
            "retries": 0,
            "status": "passed",
            "execution_time": "0.00",
            "build_time": "26.15",
            "testcases": [
                {
                    "identifier": "app.prod",
                    "execution_time": "0.00",
                    "status": "skipped",
                    "reason": "Test was built only",
                }
            ],
        }
    ]
}


def test_creating_a_tsuite_instance():
    """Test creating a list of TSuite instances.

    GIVEN a testsuite JSON object,
    WHEN creating a list of TSuite instances,
    THEN the instance should have the correct attributes.
    """
    ts = TSuite.list_from_twister_json(test_suite_json)[0]

    exp_twist_path = os.path.join(ts.board, test_suite_json["testsuites"][0]["name"])

    assert ts.name == "app.prod"
    assert ts.board == "custom_board@1.0.0_nrf52840"
    assert ts.raw_board == "custom_board@1.0.0/nrf52840"
    assert ts.path == "app"
    assert ts.twister_out_path == exp_twist_path
    assert ts.status == "passed"


def test_checking_for_a_not_ok_testsuite_status():
    """Test checking for a not OK testsuite status.

    GIVEN a testsuite JSON object with status different from "passed",
    WHEN creating a TSuite instance,
    THEN list of bad testsuites should contain an entry
    """
    bad_test_suite_json = copy.deepcopy(test_suite_json)
    bad_test_suite_json["testsuites"][0]["status"] = "failed"

    testsuites = TSuite.list_from_twister_json(bad_test_suite_json)

    assert any([ts.did_fail() for ts in testsuites])


def test_raising_exception_for_a_bad_testsuite_json():
    """Test checking for a bad testsuite json.

    testsuite json is considered bad if doesn't contain all keys expected by the TSuite
    class.

    GIVEN a testsuite JSON object with missing keys
    WHEN creating a TSuite instance,
    THEN the exception should be raised.
    """
    test_suite_json_bad = {"testsuites": [{"name": "app/app.prod"}]}

    with pytest.raises(Exception):
        _ = TSuite.list_from_twister_json(test_suite_json_bad)
