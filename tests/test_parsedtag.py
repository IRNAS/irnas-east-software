import pytest

from east.modules.parsedtag import ParsedTag
from east.modules.zephyr_semver import ZephyrSemver


def test_creating_parsedtag_when_not_in_git_repo():
    """Test creating Parsed tag when not in git repo."""
    with pytest.raises(ValueError):
        ParsedTag.from_git_describe(
            "fatal: not a git repository (or any of the parent directories): .git"
        )


def test_creating_parsedtag_without_any_commit():
    """Test creating Parsed tag when there isn't any commit in repo."""
    with pytest.raises(ValueError):
        ParsedTag.from_git_describe("fatal: bad revision 'HEAD'")


version_file_no_tag = """
VERSION_MAJOR = 0
VERSION_MINOR = 0
PATCHLEVEL = 0
VERSION_TWEAK = 0
"""


def test_creating_zephyrsemver_no_tag():
    """Test creating ZephyrSemver when aren't any tags in the git repo."""
    zs = ZephyrSemver(ParsedTag.from_git_describe("5a85363"))

    assert zs.to_string() == "v0.0.0-5a85363"
    assert zs.to_version_file() == version_file_no_tag.strip()


def test_creating_zephyrsemver_no_tag_and_dirty():
    """Test creating ZephyrSemver when aren't any tags in the git repo and state is dirty."""
    zs = ZephyrSemver(ParsedTag.from_git_describe("5a85363+"))

    assert zs.to_string() == "v0.0.0-5a85363+"
    assert zs.to_version_file() == version_file_no_tag.strip()


version_file_on_tag = """
VERSION_MAJOR = 1
VERSION_MINOR = 2
PATCHLEVEL = 3
VERSION_TWEAK = 0
"""


def test_creating_zephyrsemver_on_tag():
    """Test creating ZephyrSemver when you are directly on a clean tag."""
    zs = ZephyrSemver(ParsedTag.from_git_describe("v1.2.3-0-g98bddf3"))

    assert zs.to_string() == "v1.2.3"
    assert zs.to_version_file() == version_file_on_tag.strip()


version_file_on_dirty_tag = """
VERSION_MAJOR = 1
VERSION_MINOR = 2
PATCHLEVEL = 3
VERSION_TWEAK = 255
"""


def test_creating_zephyrsemver_on_dirty_tag():
    """Test creating ZephyrSemver when you are directly on dirty tag."""
    zs = ZephyrSemver(ParsedTag.from_git_describe("v1.2.3-0-g98bddf3+"))

    assert zs.to_string() == "v1.2.3-98bddf3+"
    assert zs.to_version_file() == version_file_on_dirty_tag.strip()


version_file_not_on_tag_clean_or_dirty = """
VERSION_MAJOR = 1
VERSION_MINOR = 2
PATCHLEVEL = 3
VERSION_TWEAK = 4
"""


def test_creating_zephyrsemver_not_on_tag():
    """Test creating ZephyrSemver when you are not directly on a tag.

    GIVEN when in git repo and not directly on a tag
    WHEN creating ParsedTag
    THEN Expected output should be returned
    """
    zs = ZephyrSemver(ParsedTag.from_git_describe("v1.2.3-4-g98bddf3"))

    assert zs.to_string() == "v1.2.3-98bddf3"
    assert zs.to_version_file() == version_file_not_on_tag_clean_or_dirty.strip()


def test_creating_zephyrsemver_not_on_tag_dirty():
    """Test creating ZephyrSemver when you are not directly on a tag and is dirty."""
    zs = ZephyrSemver(ParsedTag.from_git_describe("v1.2.3-4-g98bddf3+"))

    assert zs.to_string() == "v1.2.3-98bddf3+"
    assert zs.to_version_file() == version_file_not_on_tag_clean_or_dirty.strip()


version_file_with_extra_version = """
VERSION_MAJOR = 1
VERSION_MINOR = 2
PATCHLEVEL = 3
VERSION_TWEAK = 0
EXTRAVERSION = rc1
"""


def test_creating_zephyrsemver_with_extra_field():
    """Test creating ZephyrSemver when tag contains extra field."""
    zs = ZephyrSemver(ParsedTag.from_git_describe("v1.2.3-rc1-0-g98bddf3"))

    assert zs.to_string() == "v1.2.3-rc1"
    assert zs.to_version_file() == version_file_with_extra_version.strip()


version_file_with_extra_version_extra_dash = """
VERSION_MAJOR = 1
VERSION_MINOR = 2
PATCHLEVEL = 3
VERSION_TWEAK = 0
EXTRAVERSION = rc1-12
"""


def test_creating_zephyrsemver_with_extra_field_with_extra_dash():
    """Test creating ZephyrSemver when tag contains extra field with extra dash."""
    zs = ZephyrSemver(ParsedTag.from_git_describe("v1.2.3-rc1-12-0-g98bddf3"))

    assert zs.to_string() == "v1.2.3-rc1-12"
    assert zs.to_version_file() == version_file_with_extra_version_extra_dash.strip()


def test_giving_a_tag_without_leading_v():
    """Test creating ZephyrSemver when the tag start with v."""
    bad_tag = "1.2.3"

    valid_extensions = ["-0-g98bddf3", "-0-g98bddf3+", "-4-g98bddf3", "-4-g98bddf3+"]

    for valid_ext in valid_extensions:
        with pytest.raises(ValueError, match=r".*Tag must start with 'v'.*"):
            _ = ZephyrSemver(ParsedTag.from_git_describe(bad_tag + valid_ext))


def test_giving_a_tag_with_non_numbers():
    """Test creating ZephyrSemver when the tag doesn't contain numeric versions."""
    bad_tags = ["va.2.3", "v1.a.3", "v1.2.a"]

    valid_extensions = ["-0-g98bddf3", "-0-g98bddf3+", "-4-g98bddf3", "-4-g98bddf3+"]

    for bad_tag in bad_tags:
        for valid_ext in valid_extensions:
            with pytest.raises(ValueError, match=r".*version must be an integer.*"):
                _ = ZephyrSemver(ParsedTag.from_git_describe(bad_tag + valid_ext))


def test_giving_a_tag_with_wrong_number_of_dots():
    """Test creating ZephyrSemver when the tag doesn't follow MAJOR.MINOR.PATCH format."""
    bad_tags = ["v1", "v1.2", "v1.2.3.4"]

    valid_extensions = ["-0-g98bddf3", "-0-g98bddf3+", "-4-g98bddf3", "-4-g98bddf3+"]

    for bad_tag in bad_tags:
        for valid_ext in valid_extensions:
            with pytest.raises(ValueError, match=r".*Expected format is.*"):
                _ = ZephyrSemver(ParsedTag.from_git_describe(bad_tag + valid_ext))


version_file_with_tweak_and_extra_version = """
VERSION_MAJOR = 1
VERSION_MINOR = 2
PATCHLEVEL = 3
VERSION_TWEAK = 4
EXTRAVERSION = rc1
"""

version_file_with_tweak_and_extra_version_with_extra_dash = """
VERSION_MAJOR = 1
VERSION_MINOR = 2
PATCHLEVEL = 3
VERSION_TWEAK = 4
EXTRAVERSION = rc1-12
"""


def test_tag_from_cmd():
    """Test creating ZephyrSemver from command line."""

    def helper(ver_str, version_file):
        """Helper function for test creation ZephyrSemver from command line."""
        zs = ZephyrSemver(ParsedTag.from_cmd(ver_str))
        assert zs.to_string() == ver_str
        assert zs.to_version_file() == version_file.strip()

    helper("v0.0.0", version_file_no_tag)
    helper("v1.2.3", version_file_on_tag)
    helper("v1.2.3-rc1", version_file_with_extra_version)
    helper("v1.2.3-rc1-12", version_file_with_extra_version_extra_dash)
    helper("v1.2.3+4", version_file_not_on_tag_clean_or_dirty)
    helper("v1.2.3-rc1+4", version_file_with_tweak_and_extra_version)
    helper("v1.2.3-rc1-12+4", version_file_with_tweak_and_extra_version_with_extra_dash)
