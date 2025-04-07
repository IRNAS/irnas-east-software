from typing import NamedTuple, Optional


class ParsedTag(NamedTuple):
    """Container/interface class that holds the parsed tag information.

    The instance of this class can be created either:
    - from git describe output
    - or from a tag given on the commandline.

    The git describe command should be run with the following arguments:

        git describe --tags --always --long --dirty=+

    All possible outputs of the above command are handled:

    - No commits in the repo: fatal: bad revision 'HEAD'
    - No tags: 5a85363
    - No tags and repo is dirty: 5a85363+
    - HEAD is directly on a tag: v1.2.3-0-g98bddf3
    - HEAD is directly on a tag and repo is dirty: v1.2.3-0-g98bddf3+
    - HEAD is not directly on a tag: v1.2.3-1-g263ab82
    - HEAD is not directly on a tag and repo is dirty: v1.2.3-1-g263ab82+

    The ParsedTag object is intended to be passed to a class that does more specializes
    tag parsing, like ZephyrSemver.
    """

    tag: Optional[str]
    hash: Optional[str]
    num_commits_from_tag: Optional[int]
    dirty: bool
    on_tag: bool

    @classmethod
    def from_git_describe(cls, input: str) -> "ParsedTag":
        """Parse the output of git describe into a ParsedTag object.

        Args:
            input (str):            The output of git describe.
        """
        if (
            input
            == "fatal: not a git repository (or any of the parent directories): .git"
        ):
            # This happens when the current directory is not a git repository.
            # It is not expected that we will ever get here due to other East checks,
            # but let's handle it just in case.
            raise ValueError(
                "Not inside repository. Please run east inside a git repository."
            )

        if input == "fatal: bad revision 'HEAD'":
            # This happens when there is no commit in the repo.
            # Same thing as above.
            raise ValueError(
                "Not a single commit in the repository. Please make a commit before "
                "running east."
            )

        parts = input.split("-")

        if len(parts) == 1:
            # This happens when there are no tags in the repo.
            # The input is just the hash of the commit.
            # We can generate a default version.
            hash = parts[0]

            if "+" in hash:
                hash = hash[:-1]
                dirty = True
            else:
                dirty = False

            return cls(None, hash, 0, dirty, False)

        elif len(parts) >= 3:
            tag = "-".join(parts[:-2])
            num_commits_from_tag = int(parts[-2])
            hash = parts[-1]
            # Drop 'g' in hash
            hash = hash[1:]

            if "+" in hash:
                hash = hash[:-1]
                dirty = True
            else:
                dirty = False

            on_tag = num_commits_from_tag == 0

            return cls(tag, hash, num_commits_from_tag, dirty, on_tag)
        else:
            raise ValueError(f"Invalid git describe format: {input}")

    @classmethod
    def from_cmd(cls, tag: str) -> "ParsedTag":
        """Parse the tag from the command line into a ParsedTag object.

        Args:
            tag (str): The tag to parse.
        """
        return cls(tag, None, None, False, True)
