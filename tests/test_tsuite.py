import copy

import pytest

from east.modules.tsuite import TSuite

test_suite_json_old = {
    "environment":{
        "zephyr_version":"v3.9.99-ncs1",
    },
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

# The newer zephyr version has a change in twister which puts the build targets
# into a different directory.
# Also, the status for built-only testsuites is different.
test_suite_json_new = copy.deepcopy(test_suite_json_old)
test_suite_json_new["environment"]["zephyr_version"] = "v4.0.0-ncs1"
test_suite_json_new["testsuites"][0]["status"] = "not run"

@pytest.mark.parametrize(
    "twister_json, expected_twister_out_path, expected_status",
    [
        (test_suite_json_old, "custom_board@1.0.0_nrf52840/app/app.prod", "passed"),
        (test_suite_json_new, "custom_board@1.0.0_nrf52840/zephyr/app/app.prod", "not run"),
    ],
)
def test_creating_a_tsuite_instance(twister_json, expected_twister_out_path, expected_status):
    """Test creating a list of TSuite instances.

    GIVEN a testsuite JSON object,
    WHEN creating a list of TSuite instances,
    THEN the instance should have the correct attributes.
    """
    ts = TSuite.list_from_twister_json(twister_json)[0]

    # exp_twist_path = os.path.join(ts.board, twister_json["testsuites"][0]["name"])

    assert ts.name == "app.prod"
    assert ts.board == "custom_board@1.0.0_nrf52840"
    assert ts.raw_board == "custom_board@1.0.0/nrf52840"
    assert ts.path == "app"
    assert ts.twister_out_path == expected_twister_out_path
    assert ts.status == expected_status


def test_checking_for_a_failed_testsuite_status():
    """Test checking for a failed testsuite status.

    GIVEN a testsuite JSON object with status "failed",
    WHEN creating a TSuite instance,
    THEN list of bad testsuites should contain an entry
    """
    bad_test_suite_json = copy.deepcopy(test_suite_json_old)
    bad_test_suite_json["testsuites"][0]["status"] = "failed"

    testsuites = TSuite.list_from_twister_json(bad_test_suite_json)

    assert any([ts.did_fail() for ts in testsuites])


@pytest.mark.parametrize(
    "twister_json",
    [
        test_suite_json_old,
        test_suite_json_new,
    ],
)
def test_checking_for_all_built_testsuite(twister_json):
    """Test checking for a built testsuite.

    GIVEN a testsuite JSON object with all testsuites successfully built,
    WHEN creating a TSuite instance,
    THEN all testsuites should be marked as built.
    """
    testsuites = TSuite.list_from_twister_json(twister_json)

    assert all([ts.did_build() for ts in testsuites])

@pytest.mark.parametrize(
    "twister_json",
    [
        test_suite_json_old,
        test_suite_json_new,
    ],
)
def test_checking_for_not_built_testsuite(twister_json):
    """Test checking for a not built testsuite.

    GIVEN a testsuite JSON object with at least one testsuite not built successfully,
    WHEN creating a TSuite instance,
    THEN at least one testsuite should be marked as not built.
    """
    not_built_test_suite_json = copy.deepcopy(twister_json)
    not_built_test_suite_json["testsuites"][0]["status"] = "failed"

    testsuites = TSuite.list_from_twister_json(not_built_test_suite_json)

    assert any([not ts.did_build() for ts in testsuites])


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
