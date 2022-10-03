import os

HOME_DIR = os.path.join("/home", os.environ["USER"])

# Directory that can be used for temporary intermediate files that we do not care about.
CACHE_DIR = os.path.join(HOME_DIR, ".cache", "east")

# East directory, any files that east needs to function normally are located here
EAST_DIR = os.path.join(HOME_DIR, ".local", "share", "east")

# Path to the toolchain executable, ignore the .exe extension, this works as it should
NRF_TOOLCHAIN_MANAGER_PATH = os.path.join(EAST_DIR, "nrfutil-toolchain-manager.exe")

# Directory will all Conda stuff
MINICONDA_DIR = os.path.join(HOME_DIR, "miniconda3")

# Path to the Conda executable, this can be used when the conda is not yet on PATH
CONDA_PATH = os.path.join(MINICONDA_DIR, "bin", "conda")
