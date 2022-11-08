import click

from ..east_context import east_command_settings


def get_build_types(project_key):
    project_key


@click.command(**east_command_settings)
@click.option(
    "-s",
    "--software-version",
    type=str,
    help="Version of the software, it should be in '0.0.0' format",
)
@click.pass_obj
def release(east, software_version):
    """
    Create a release.

    \b
    \n\nChecks east.yaml




    \n\n[bold]Note:[/] This command can be only run from inside of a [bold yellow]West workspace[/].
    """

    east.pre_workspace_command_check()

    # Locate east.yaml which should be in the projects directory.

    # Release process:
    # for each project:
    #   for each west_board
    #     for each of its hv_versions
    #       for every build type
    #         Run west build command with correct conf files

    for project in conf["projects"]:
        build_types = project["build-types"]

        for west_board in project["west-boards"]:
            if "hv_versions" in west_board:
                for hv_version in west_board["hv_versions"]:
                    east.print(hv_version)
