from typing import Tuple

from .parsedtag import ParsedTag


def _parse_tag(tag: str) -> Tuple[int, int, int, str, int]:
    """Parse a tag.

    This function contains logic to parse the semver-like tag into structured data.

    The tweak part is only relevant for the cases where the tag is given on the
    command line.
    """
    if not tag.startswith("v"):
        raise ValueError(f"Invalid tag format: {tag}. Tag must start with 'v'.")

    # Drop 'v' in a tag
    tag_part = tag[1:]

    if "+" in tag_part:
        # We have a tweak
        split = tag_part.split("+")
        tweak = _parse_int_version(split[-1], tag, "Tweak")
        # Join back the rest
        tag_part = "+".join(split[:-1])
    else:
        # No tweak
        tweak = 0

    if "-" in tag_part:
        # We have an extra part
        split = tag_part.split("-")
        tag_part = split[0]
        # Join back the rest
        extra = "-".join(split[1:])
    else:
        # No extra
        extra = ""

    # Split at "." and "-". Check how many parts we have.
    parts = tag_part.split(".")

    if len(parts) != 3:
        raise ValueError(
            f"Invalid tag format: {tag}. Expected format is vMAJOR.MINOR.PATCH[-extra]."
        )

    # Major, minor and patch are required
    major = _parse_int_version(parts[0], tag, "Major")
    minor = _parse_int_version(parts[1], tag, "Minor")
    patch = _parse_int_version(parts[2], tag, "Patch")

    def check_255_limit(ver, name):
        """Check if the version part is within the 255 limit.

        This is needed as the Zephyr' VERSION file only alloacates 1 byte for each
        field.
        """
        if ver > 255:
            raise Exception(
                f"{name} (ver) exceeded limit of 1 byte (255). Zephyr's "
                "VERSION file only allows 1 byte for each field."
            )
        return ver

    def clamp_tweak(tweak):
        """Clamp tweak number to 255, if above that.

        Zephyr's VERSION file only alloacates 1 byte for the tweak field. However, in
        the case of the tweak we clamp it to 255, instead of erroring, since being 255
        commits from the tag is a valid use case.
        """
        if tweak > 255:
            print(f"Warning: Tweak number ({tweak}) exceeds 255, clamping it to 255.")
            return 255
        return tweak

    major = check_255_limit(major, "major")
    minor = check_255_limit(minor, "minor")
    patch = check_255_limit(patch, "patch")
    tweak = clamp_tweak(tweak)

    return major, minor, patch, extra, tweak


def _parse_int_version(part: str, tag: str, annotation: str) -> int:
    """Try to parse an integer version part, such as major, minor, or patch.

    Returns:
        int: The parsed integer version part.
    """
    try:
        return int(part)
    except Exception:
        raise ValueError(
            f"Invalid tag format: {tag}\n{annotation} version must be an integer."
        )


class ZephyrSemver:
    """Zephyr Semver tag parser class.

    This class has some expectations about the tag field that is contained by given
    ParsedTag object.

    - The pt.tag should be in format:

        vMAJOR.MINOR.PATCH[-EXTRA][+TWEAK].

    MAJOR, MINOR and PATCH are required, EXTRA and TWEAK are optional.
    Only EXTRA can be an alphanumeric string, the rest must be integers.


    Specific to the TWEAK number:

    - If pt.num_commits_from_tag is set, then TWEAK is set to it.
    - Otherwise it is set as determined by the pt.tag (if not given it is set to 0).


    The Zephyr Semver object can then be represented:

    - as a string, using the to_string() method. The output format is:

        vMAJOR.MINOR.PATCH[-EXTRA][-HASH[+]][+TWEAK]

    - or as a Zephyr VERSION file.


    Specific to the to_string() representation:

    - If the self.tweak is equal to 0, it will not appear in the string representation.
    - The plus '+' after the HASH part will only appear if the repo was dirty.
    - to_string() representation will only contain HASH part if HASH was given and
      pt.on_tag is False.

    Specific to the to_version_file() representation:
    - VERSION_TWEAK will be set to 255, if HEAD was on tag, but repo was dirty.
    """

    def __init__(self, pt: ParsedTag):
        """Create a ZephyrSemver object from a ParsedTag object.

        See the class docstring for the expectations about the tag.

        Args:
            pt (ParsedTag): The parsed tag to take the data from.
        """
        self.hash = pt.hash
        self.dirty = pt.dirty
        self.on_tag = pt.on_tag

        if not pt.tag:
            self.major = 0
            self.minor = 0
            self.patch = 0
            self.extra = ""
            self.tweak = 0
            return

        self.major, self.minor, self.patch, self.extra, self.tweak = _parse_tag(pt.tag)

        # Override the tweak number if we have num_commits_from_tag, otherwise
        # use value from the _parse_tag
        if pt.num_commits_from_tag:
            self.tweak = pt.num_commits_from_tag

        if self.on_tag and self.dirty:
            # We are directly on a dirty tag
            self.tweak = 255

    def to_string(self) -> str:
        """Convert the object to a string representation.

        Returns:
            str: The string representation of the ParsedTag object.
        """
        ver = f"v{self.major}.{self.minor}.{self.patch}"

        if self.extra:
            ver += f"-{self.extra}"

        if not self.hash:
            # If there is no hash it means that from_cmd() was used.
            if self.tweak:
                ver += f"+{self.tweak}"
            return ver

        # We have a hash
        if self.dirty:
            ver += f"-{self.hash}+"
        elif not self.on_tag and not self.dirty:
            ver += f"-{self.hash}"

        return ver

    def to_version_file(self) -> str:
        """Convert the object to a VERSION file representation.

        Returns:
            str: The VERSION file representation of the ParsedTag object.
        """
        f = [
            f"VERSION_MAJOR = {self.major}",
            f"VERSION_MINOR = {self.minor}",
            f"PATCHLEVEL = {self.patch}",
            f"VERSION_TWEAK = {self.tweak}",
        ]

        if self.extra:
            f.append(f"EXTRAVERSION = {self.extra}")

        return "\n".join(f)
