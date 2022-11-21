from click.testing import CliRunner
from setuptools_scm import get_version

from east.__main__ import cli


def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0

    assert (
        get_version(version_scheme="post-release", local_scheme="no-local-version")
        in result.output
    )
