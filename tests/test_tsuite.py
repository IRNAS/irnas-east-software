import copy

import pytest

from east.modules.tsuite import TSuite

test_suite_json = {
    # This is a Zephyr v3 "style" testsuite
    "testsuites": [
        {
            "name": "app/app.v3",
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
                    "identifier": "app.v3",
                    "execution_time": "0.00",
                    "status": "skipped",
                    "reason": "Test was built only",
                }
            ],
        },
        # This is a Zephyr v4 "style" testsuite
        {
            "name": "app/app.v4",
            "arch": "arm",
            "platform": "custom_board@1.0.0/nrf52840",
            "path": "../project/app",
            "run_id": "953b256c22f70c8293b9b625baea26ef",
            "runnable": False,
            "retries": 0,
            "status": "not run",
            "execution_time": "0.00",
            "build_time": "26.15",
            "toolchain": "zephyr",
            "testcases": [
                {
                    "identifier": "app.v4",
                    "execution_time": "0.00",
                    "status": "not run",
                    "reason": "Test was built only",
                }
            ],
        },
        # This is a Zephyr v4 "style" testsuite for native sim
        {
            "name": "app/app.native",
            "arch": "arm",
            "platform": "native_sim/native",
            "path": "../project/app",
            "run_id": "953b256c22f70c8293b9b625baea26ef",
            "runnable": False,
            "retries": 0,
            "status": "not run",
            "execution_time": "0.00",
            "build_time": "26.15",
            "toolchain": "host",
            "testcases": [
                {
                    "identifier": "app.native",
                    "execution_time": "0.00",
                    "status": "not run",
                    "reason": "Test was built only",
                }
            ],
        },
        # This is a testsuite that was filtered out
        # This happens on older NCSs. On new ones, filtered testsuites are
        # not in twister.json at all.
        #
        # After parsing, it should not appear in any TSuite list
        {
            "name": "app/app.filtered",
            "arch": "arm",
            "platform": "custom_board@1.0.0/nrf52840",
            "path": "../project/app",
            "run_id": "953b256c22f70c8293b9b625baea26ef",
            "runnable": False,
            "retries": 0,
            "status": "filtered",
            "execution_time": "0.00",
            "build_time": "26.15",
            "toolchain": "host",
            "testcases": [
                {
                    "identifier": "app.filtered",
                    "execution_time": "0.00",
                    "status": "filtered",
                    "reason": "Not in testsuite platform allow list",
                }
            ],
        },
    ],
}


def test_creating_tsuite_instances():
    """Test creating a list of TSuite instances.

    GIVEN a testsuite JSON object,
    WHEN creating a list of TSuite instances,
    THEN the instance should have the correct attributes.
    """
    ts = TSuite.list_from_twister_json(test_suite_json)

    # With this assertion we ensure that the testsuite JSON
    # contains the expected number of testsuites.
    # The fourth testsuite is filtered out, so it should not be in the list.
    assert len(ts) == 3

    v3 = ts[0]
    v4 = ts[1]
    native = ts[2]

    assert v3.name == "app.v3"
    assert v3.board == "custom_board@1.0.0_nrf52840"
    assert v3.raw_board == "custom_board@1.0.0/nrf52840"
    assert v3.path == "app"
    assert v3.twister_out_path == "custom_board@1.0.0_nrf52840/app/app.v3"
    assert v3.status == "passed"

    assert v4.name == "app.v4"
    assert v4.board == "custom_board@1.0.0_nrf52840"
    assert v4.raw_board == "custom_board@1.0.0/nrf52840"
    assert v4.path == "app"
    assert v4.twister_out_path == "custom_board@1.0.0_nrf52840/zephyr/app/app.v4"
    assert v4.status == "not run"

    assert native.name == "app.native"
    assert native.board == "native_sim_native"
    assert native.raw_board == "native_sim/native"
    assert native.path == "app"
    assert native.twister_out_path == "native_sim_native/host/app/app.native"
    assert native.status == "not run"


def test_checking_for_a_failed_testsuite_status():
    """Test checking for a failed testsuite status.

    GIVEN a testsuite JSON object with status "failed",
    WHEN creating a TSuite instance,
    THEN list of bad testsuites should contain an entry
    """
    bad_test_suite_json = copy.deepcopy(test_suite_json)
    bad_test_suite_json["testsuites"][0]["status"] = "failed"

    testsuites = TSuite.list_from_twister_json(bad_test_suite_json)

    assert any([ts.did_fail() for ts in testsuites])


def test_checking_for_all_built_testsuite():
    """Test checking for a built testsuite.

    GIVEN a testsuite JSON object with all testsuites successfully built,
    WHEN creating a TSuite instance,
    THEN all testsuites should be marked as built.
    """
    testsuites = TSuite.list_from_twister_json(test_suite_json)

    assert all([ts.did_build() for ts in testsuites])


def test_checking_for_not_built_testsuite():
    """Test checking for a not built testsuite.

    GIVEN a testsuite JSON object with at least one testsuite not built successfully,
    WHEN creating a TSuite instance,
    THEN at least one testsuite should be marked as not built.
    """
    not_built_test_suite_json = copy.deepcopy(test_suite_json)
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
