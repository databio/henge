#! /usr/bin/env python

import os
from setuptools import setup
import sys

PACKAGE = "henge"

# Additional keyword arguments for setup().
extra = {}

# Ordinary dependencies
DEPENDENCIES = []
with open("requirements/requirements-all.txt", "r") as reqs_file:
    for line in reqs_file:
        if not line.strip():
            continue
        DEPENDENCIES.append(line)

extra["install_requires"] = DEPENDENCIES

with open("{}/_version.py".format(PACKAGE), "r") as versionfile:
    version = versionfile.readline().split()[-1].strip("\"'\n")

# Handle the pypi README formatting.
long_description = open("README.md").read()

setup(
    name=PACKAGE,
    packages=[PACKAGE],
    version=version,
    description="Storage and retrieval of object-derived, decomposable recursive unique identifiers.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: System :: Distributed Computing",
    ],
    keywords="",
    url="https://databio.org",
    author="Nathan Sheffield",
    author_email="nathan@code.databio.org",
    license="BSD2",
    entry_points={
        "console_scripts": ["packagename = packagename.packagename:main"],
    },
    package_data={"packagename": [os.path.join("packagename", "*")]},
    include_package_data=True,
    test_suite="tests",
    tests_require=(["pytest"]),
    setup_requires=(
        ["pytest-runner"] if {"test", "pytest", "ptr"} & set(sys.argv) else []
    ),
    **extra
)
