# East configuration

The east tool provides a way to specify project-specific configuration. The
configuration is done with an `east.yml` file, which needs to be placed in
the root directory of the repo.

Currently, the configuration is required for:
* specifying available build types for applications and samples,
* specifying binary assets for the release command.

## General structure of the configuration file

`east.yml` contains two main keys:

- `apps` - lists one or more applications with their own specific
  configurations.
- `samples` - lists one or more samples which can inherit configurations from
  applications.

East also introduces a concept of a _build type_ for building several images
that only differ from each other in KConfig options.

## Build type

Build types are sets of Kconfig fragment files (`.conf` files) that are given to
CMake during the build system generation process.

Splitting your Kconfig fragments into distinct files means that we:
* have a clear separation of concerns, each fragment deals with one specific
  idea,
* can have better reuse of configuration files between different projects,
* do not have to repeat the same sets of settings in different files, thus
  lowering the chance of copy-paste mistakes.

The user specifies the exact set of Kconfig fragments for each build type in
`east.yml`:

```yaml
apps:
  - name: template
    path: app
    west-boards:
      - board: custom_nrf52840dk
      - board: nrf52840dk_nrf52840

    build-types:
      - type: prod
      - type: debug
        conf-files:
          - debug.conf
      - type: uart
        conf-files:
          - debug.conf
          - uart.conf
```

When building an application image the user can specify the specific build type with
`--build-type` or `-u` flag, , for example:

```bash
east build -b nrf52840dk_nrf52840 --build-type debug
```

There are a few rules that are related to the build types and the way 
they are specified in `east.yml`:

- Each application needs to contain a `confs` folder which stores all conf files
  for that application. East will look for listed `conf-files` inside this
  folder.
- Each `confs` folder is required to contain a `common.conf` file which
  contains configuration _common_ to all build types. `common.conf` replaces the
  role of `prj.conf`, which is now not allowed to be used in applications (in
  samples it is still allowed).
- `common.conf` is always used with each build type, so it does not need to be
  explicitly specified in `conf-files`.
- the `prod` build type (stands for _production_) always needs to exist. It uses
  just `common.conf`. `prod` build type is the default built type, meaning that
  if `--build-type` is not specified in the `east build` command then `prod` is
  used.
- Order of additional conf.files matters, as they are applied in the order
  listed.
- As normal, conf files that are specific to the used west boards,
  (`nrf52840dk_nrf52840.conf`) for example, are picked up automatically, however
  they also need to be placed within the `confs` folder.

For example, taking the above rules and the example `east.yml` into account this
means that:

* When we do not specify the build type, the `prod` build type is used, which
  means only `common.conf` is used.
* When we use `prod` build type, only `common.conf` is used.
* When we use `debug` build type, `common.conf` and `debug.conf` are used.
* When we use `uart` build type, `common.conf`, `debug.conf` and  `uart.conf`
  are used.

## Applications

The applications is the main program in an east workspace. It should be placed into
the `app` folder (or `apps` if there are more than one). The most common use-case is a
GitHub repo with one application, however repos with multiple applications are also
supported.

To configure an application in `east.yml`, the user must
specify which `west-boards` and `build-types` are available.

Listed `west-boards` do not matter for the `east build` command, as it does not
check against them. They do however matter for the `east release` command, which
needs them so it can know for which boards to build a release.

Each application needs to specify the `path` key, which is the path to the
application's `CmakeLists.txt`, relative to the `east.yml` file.

## Samples

These are small programs that are located in the `samples` folder. Their purpose
is to test or demonstrate some specific module or library.

They do not require `confs` folders (as they are expected to test only one thing),
however, we can add KConfig fragment files to them in two ways:
* We can specify all settings in a `prj.conf` file in the samples folder, which
  is picked up by west (and thus east) automatically,
* Or we use the `inherit-build-type` key in `east.yaml` to specify which
  `build-types` from which `app` we would like to use.

In both cases we do not need to specify the `--build-type` option, east will
figure out what to do. By specifying the sample in the `east.yml` file it means
that it will be picked up by the `east release` command, which is the _best
practice_ as that way you are forced to keep samples up to date. That being
said, samples do not need to be specified in the `east.yml` file for the east
`build command` to work (but you can only use `prj.conf` in that case).

An example sample section is below, imagine that it is below the above snippet
which is in _Build types section_:

```yaml
samples:
  - name: settings
    west-boards:
      - board: custom_nrf52840dk
    inherit-build-type:
        app: template
        build-type: debug

  - name: dfu
    west-boards:
      - board: custom_nrf52840dk
    # Don't inherit, use prj.conf in the sample's folder.

```


## Release command

Command `east release` builds every single combination of firmware which is
listed in the `east.yml` file.

Different hardware versions of listed boards are picked up automatically from
the `board` directory.

Generally this means:
```
* Create a binary for each `app`
    * for each hardware version of the `west-board`
        * for each `build-type`
```
and
```
* Create a binary for each `sample`
    * for each hardware version of the `west-board`
        * for each `build-type` (either inherited or just `prj.conf`)
```

Created binaries are named according to the [IRNAS's release artefact naming
guidelines]. Samples are placed into a separate folder to avoid confusion.

`east release` accepts the software version which is injected in the binaries
(this depends on the modules used) and is added to the created file names.

[IRNAS's release artefact naming guidelines]: https://github.com/IRNAS/irnas-guidelines-docs/blob/dev/docs/github_projects_guidelines.md#release-artefacts-naming-scheme-
