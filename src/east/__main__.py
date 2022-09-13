import click


@click.command()  # @cli, not @click!
def test():
    click.echo("Testing")


@click.group()
@click.version_option(message="v%(version)s")
def cli():
    pass


cli.add_command(test)


def main():
    cli()


if __name__ == "__main__":
    main()
