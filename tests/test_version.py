from click.testing import CliRunner
from east.__main__ import cli


def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "v0.0.0" in result.output


if __name__ == "__main__":
    test_version()
    pass
