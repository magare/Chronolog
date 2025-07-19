#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="chronolog",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "watchdog>=3.0.0",
        "click>=8.1.0",
        "colorama>=0.4.6",
        "psutil>=5.9.0",
    ],
    entry_points={
        "console_scripts": [
            "chronolog=chronolog.cli:main",
        ],
    },
    python_requires=">=3.9",
)