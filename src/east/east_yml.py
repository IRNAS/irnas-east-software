import os

import pykwalify.core
import pykwalify.errors
import yaml

from .helper_functions import return_dict_on_match


class EastYmlLoadError(RuntimeError):
    """Some error happened when trying to load east.yml."""


def format_east_yml_load_error_msg(exception_msg):
    """Format error message for EastYmlLoadError.

    Use this to format error messages that happen when trying to load east.yml
    """
    return (
        "An [bold red]error[/] occurred when trying to load [bold yellow]east.yml[/]"
        f" file!\n\n[italic yellow]{exception_msg}[/]\n"
    )


def load_east_yml(project_dir: str):
    """Try to load east.yml. If that succeeds validate it.

        project_dir (str): Path to project directory, where east.yml should be located.

    Returns:
        dict with east.yml contents if east.yml is found and correctly validated. If it
        can not be found it returns None.

    """
    east_yml = os.path.join(project_dir, "east.yml")

    if not os.path.isfile(east_yml):
        return None

    # Validate yaml
    schema_yml = os.path.join(os.path.dirname(__file__), "configuration-schema.yaml")
    try:
        c = pykwalify.core.Core(source_file=east_yml, schema_files=[schema_yml])
    except pykwalify.errors.CoreError:
        # This error is raised when east.yml is empty, which is allowed.
        return None

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

    # This is needed to discern between apps key present, apps key present, but not set
    # and not app key at all.
    apps = east_yml.get("apps", -1)

    # apps are optional
    if apps is not None and apps != -1:
        check_duplicated_entries(east_yml["apps"], "apps", "name")
        for app in east_yml["apps"]:
            if "build-types" in app:
                check_duplicated_entries(
                    app["build-types"], f"{app['name']}.build-types", "type"
                )

    if apps is None:
        # Exists, but it was not set
        raise EastYmlLoadError(
            "[bold]apps[/] key in [bold yellow]east.yml[/] has no apps listed under it!"
        )

    # samples are optional
    if east_yml.get("samples"):
        check_duplicated_entries(east_yml["samples"], "samples", "name")
        # For each sample that has inherit key check if that app with that build type
        # exists
        for sample in east_yml["samples"]:
            if "inherit-build-type" in sample:
                # Inherit needs apps
                if not east_yml.get("apps"):
                    raise EastYmlLoadError(
                        f"Sample [bold]{sample['name']}[/] is trying to inherit, but"
                        " there are no apps to inherit from!"
                    )

                inherited_app = sample["inherit-build-type"]["app"]
                inherited_type = sample["inherit-build-type"]["build-type"]

                app = return_dict_on_match(east_yml["apps"], "name", inherited_app)
                if not app:
                    raise EastYmlLoadError(
                        f"Sample [bold]{sample['name']}[/] is trying to inherit from a"
                        f" [bold red]non-existing[/] app [bold]{inherited_app}[/]."
                    )
                # Release build type is special, apps always have it implicitly, so we
                # do not have to search for it.
                if inherited_type != "release":
                    if "build-types" not in app or not return_dict_on_match(
                        app["build-types"], "type", inherited_type
                    ):
                        raise EastYmlLoadError(
                            f"Sample [bold]{sample['name']}[/] is trying to inherit "
                            "from a [bold red]non-existing[/] build-type"
                            f" [bold]{inherited_type}[/]."
                        )
    # pack is optional
    if east_yml.get("pack"):
        common_artifacts = east_yml["pack"].get("artifacts", [])
        check_for_duplicated_items_in_list(common_artifacts, "pack.artifacts")

        if "build_configurations" in east_yml["pack"]:
            check_duplicated_entries(
                east_yml["pack"]["build_configurations"],
                "pack.build_configurations",
                "name",
            )

            # Validation loop
            for p in east_yml["pack"]["build_configurations"]:
                if "artifacts" in p and "overwrite_artifacts" in p:
                    raise EastYmlLoadError(
                        "Both [bold]artifacts[/] and [bold]overwrite_artifacts[/] fields "
                        f"are set for the [bold]pack.project.{p['name']}[/] in the "
                        "[bold]east.yml[/], this is not allowed!"
                    )
                if "artifacts" not in p and "overwrite_artifacts" not in p:
                    raise EastYmlLoadError(
                        f"[bold]pack.project.{p['name']}[/] field should have atleast one "
                        "of [bold]artifacts[/] and [bold]overwrite_artifacts[/] fields but "
                        "it has none!"
                    )

                if "artifacts" in p:
                    check_for_duplicated_items_in_list(
                        p["artifacts"],
                        f"combined pack.artifact and pack.project.{p['name']}.artifacts",
                    )
                    check_for_duplicated_items_in_list(
                        common_artifacts + p["artifacts"],
                        f"pack.project.{p['name']}.artifacts",
                    )

                if "overwrite_artifacts" in p:
                    check_for_duplicated_items_in_list(
                        p["overwrite_artifacts"],
                        f"pack.project.{p['name']}.overwrite_artifacts",
                    )

    # version is optional
    if east_yml.get("version"):
        check_for_duplicated_items_in_list(
            east_yml["version"]["paths"], "version.paths"
        )

    return east_yml


def check_for_duplicated_items_in_list(x: list, field_name: str):
    """Raise exception if x contains duplicate entries."""
    if len(x) != len(set(x)):
        raise EastYmlLoadError(
            f"Found duplicated artifacts under [bold]{field_name}[/]."
        )
