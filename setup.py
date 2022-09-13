import os
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt") as f:
    required = f.read().splitlines()

VERSION = os.getenv('EAST_VERSION')

# No version was given at package build time, probably dev build.
if not VERSION:
    VERSION = "v0.0.0"


setup(
    name="east",
    version=VERSION,
    author="Marko Sagadin",
    author_email="marko.sagadin42@gmail.com",
    description="Tool built on top of West for managing nRF Connect SDK projects.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MarkoSagadin/proto-east-python",
    license="MIT",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=required,
    python_requires=">=3.8",
    entry_points={"console_scripts": ("east = east.__main__:main",)},
)
