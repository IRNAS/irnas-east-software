import os

import pykwalify.core
import yaml

from .helper_functions import return_dict_on_match


class EastYmlLoadError(RuntimeError):
    """Some error happened when trying to load east.yml."""


east_yml_load_error_msg = """
[bold yellow]east.yml[/] was [bold red]not found[/] in the project's root directory!

See documentation on how to create it.
"""
# TODO: Provide a better help string, by recommending east help config command, when it
# is implemented


def format_east_yml_load_error_msg(exception_msg):
    """Use this to format error messages that happen when trying to load east.yml"""
    return (
        "An [bold red]error[/] occurred when trying to load [bold yellow]east.yml[/]"
        f" file!\n\nError message:\n\n\t[italic yellow]{exception_msg}[/]\n"
    )


def load_east_yml(project_dir: str):
    east_yml = os.path.join(project_dir, "east.yml")

    if not os.path.isfile(east_yml):
        raise EastYmlLoadError(east_yml_load_error_msg)

    # Validate yaml
    schema_yml = os.path.join(os.path.dirname(__file__), "configuration-schema.yaml")
    c = pykwalify.core.Core(source_file=east_yml, schema_files=[schema_yml])
    try:
        c.validate(raise_exception=True)
    except pykwalify.core.SchemaError as e:
        raise EastYmlLoadError(e)

    # Load file
    with open(east_yml, "r") as file:
        east_yml = yaml.safe_load(file)

    # Handle duplicated entries in app name, samples names and build types under each
    # app
    def check_duplicated_entries(array_of_dicts, printed_key, subkey):
        names = [ele[subkey] for ele in array_of_dicts]
        if len(names) > len(set(names)):
            raise EastYmlLoadError(
                f"Found duplicated [bold]{subkey}s[/] under [bold]{printed_key}[/] key"
                " in [bold]east.yml[/]!"
            )

    check_duplicated_entries(east_yml["apps"], "apps", "name")
    check_duplicated_entries(east_yml["samples"], "samples", "name")
    for app in east_yml["apps"]:
        check_duplicated_entries(
            app["build-types"], f"{app['name']}.build-types", "type"
        )

    # For each sample that has inherit key check if that app with that build type exists
    for sample in east_yml["samples"]:
        if "inherit-build-type" in sample:
            inherited_app = sample["inherit-build-type"]["app"]
            inherited_type = sample["inherit-build-type"]["build-type"]

            app = return_dict_on_match(east_yml["apps"], "name", inherited_app)
            if not app:
                raise EastYmlLoadError(
                    f"Sample [bold]{sample['name']}[/] is trying to inherit from a"
                    f" [bold red]non-existing[/] app [bold]{inherited_app}[/]."
                )
            if not return_dict_on_match(app["build-types"], "type", inherited_type):
                raise EastYmlLoadError(
                    f"Sample [bold]{sample['name']}[/] is trying to inherit from a"
                    f" [bold red]non-existing[/] build-type [bold]{inherited_type}[/]."
                )

    return east_yml
