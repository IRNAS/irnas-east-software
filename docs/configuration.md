# East configuration

The `east` tool provides a way to specify the project-specific configuration. The configuration is
done with an `east.yml` file, which needs to be placed in the _root directory_ of the repository.

Currently, the configuration is required for:

- specifying which files should be copied when using `east pack`,
- specifying where to place VERSION files when using `east util version`.

The `east.yml` file is optional; Users do not need to create it in order to use `east`. However in
that case, the above functionalities will not work.

This document describes the expected contents of `east.yml` and how to specify binary assets for the
`east pack` command.

## General structure of the configuration file

`east.yml` contains two main keys:

- `pack` - lists which artifacts to be copied when using `east pack` for all or for specific
  applications and samples.
- `version` - lists directories into which `east` will place VERSION files when using
  `east util version` command. See `east util version --help` for more details.

<!-- prettier-ignore -->
> [!NOTE]
> The `app` and `samples` yaml keys are deprecated.
> See the [old documentation](configuration_old.md) for their use.

Below is an example of `east.yml` that can be copied into a project and modified:

```yaml
pack:
  artifacts:
    - $APP_DIR/zephyr/zephyr.hex
    - $APP_DIR/zephyr/zephyr.bin
    - merged.hex
  build_configurations:
    - name: sample.blinky
      overwrite_artifacts:
        - $APP_DIR/zephyr/zephyr.hex
  extra:
    - scripts/some_script/some_script.sh
    - scripts/generated_extra_stuff.zip

version:
  paths:
    - app/
```

For details on east pack, see the [Packing document](./pack.md).
