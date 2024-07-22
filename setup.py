import glob
import os
import unittest

from setuptools import find_packages, setup
from setuptools.command.build_py import build_py

with open("README.md", "rt") as fh:
    long_description = fh.read()

with open("requirements.txt", "rt") as f:
    requirements = [r.strip() for r in f.readlines()]



class PublishCommand(build_py):
    """Publish package to PyPI"""
    def run(self):
        os.system("rm -rf dist")
        os.system("python3 setup.py sdist"
                  "&& python3 setup.py bdist_wheel"
                  "&& python3 -m twine upload dist/*whl dist/*gz")

setup(
    name='llm_utils',
    version="0.1",
    description="Utilities for querying large language model (LLM) APIs include those from Anthropic, OpenAI, Mistral, and Gemini",
    install_requires=requirements,
    cmdclass={
        'publish': PublishCommand,
    },
    entry_points = {},
    long_description_content_type="text/markdown",
    long_description=long_description,
    packages=["llm_utils"],
    include_package_data=True,
    python_requires=">=3.7",
    license="MIT",
    keywords="",
    url='https://github.com/bw2/llm-utils',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
)
