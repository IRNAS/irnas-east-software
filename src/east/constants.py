import os

# From this file only dict consts_path should be imported, and this should happen only
# in __main__.
# There are however exceptions: NRFUTIL_PATH, CPPCHECK_PATH,
# CLANG_PATH, CODECHECKER_PATH are needed for downloading in install.py.

HOME_DIR = os.environ["HOME"]

# Directory that can be used for temporary intermediate files that we do not care about.
CACHE_DIR = os.path.join(HOME_DIR, ".cache", "east")

# East directory, any files that east needs to function normally are located here.
EAST_DIR = os.path.join(HOME_DIR, ".local", "share", "east")

# Tooling directory, for all the tools that east uses.
TOOLING_DIR = os.path.join(EAST_DIR, "tooling")

# Path to the nrfutil executable.
NRFUTIL_PATH = os.path.join(TOOLING_DIR, "nrfutil", "nrfutil")

# Path to the cppcheck executable.
CPPCHECK_PATH = os.path.join(TOOLING_DIR, "cppcheck", "cppcheck")

# Path to the clang executables.
CLANG_BIN_PATH = os.path.join(TOOLING_DIR, "clang+llvm", "bin")
CLANG_PATH = os.path.join(CLANG_BIN_PATH, "clang")
CLANG_TIDY_PATH = os.path.join(CLANG_BIN_PATH, "clang-tidy")
CLANG_REPLACE_PATH = os.path.join(CLANG_BIN_PATH, "clang-apply-replacements")

# Path to the CodeChecker executable.
CODECHECKER_PATH = os.path.join(
    TOOLING_DIR, "codechecker", "build", "CodeChecker", "bin", "CodeChecker"
)

if os.environ.get("EAST_CODECHECKER_CI_MODE", "0") == "1":
    # In CI mode, the CodeChecker executable is not in the tooling directory, but in
    # the system path.
    CODECHECKER_PATH = "CodeChecker"

# Directory will all Conda stuff.
MINICONDA_DIR = os.path.join(HOME_DIR, "miniconda3")

# Path to the Conda executable, this can be used when the Conda is not yet on PATH.
CONDA_PATH = os.path.join(MINICONDA_DIR, "bin", "conda")

const_paths = {
    "cache_dir": CACHE_DIR,
    "east_dir": EAST_DIR,
    "tooling_dir": TOOLING_DIR,
    "nrfutil_path": NRFUTIL_PATH,
    "miniconda_dir": MINICONDA_DIR,
    "conda_path": CONDA_PATH,
    "cppcheck_path": CPPCHECK_PATH,
    "clang_path": CLANG_PATH,
    "clang_tidy_path": CLANG_TIDY_PATH,
    "clang_replace_path": CLANG_REPLACE_PATH,
    "codechecker_path": CODECHECKER_PATH,
}
