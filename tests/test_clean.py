import os

from click.testing import CliRunner

from east.__main__ import cli


def test_clean_command(west_workplace_parametrized):
    """Test the clean command."""
    _ = west_workplace_parametrized

    runner = CliRunner()

    os.mkdir("build")
    assert "build" in os.listdir()

    result = runner.invoke(cli, ["clean"])

    assert result.exit_code == 0
    assert "build" not in os.listdir()
