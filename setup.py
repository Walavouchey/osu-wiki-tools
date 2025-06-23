# type: ignore
import setuptools

from wikitools_cli.VERSION import VERSION


with open("README.md", "r", encoding="utf-8") as fd:
    long_description = fd.read()

with open("requirements.txt", "r", encoding="utf-8") as fd:
    requirements = fd.read().splitlines()

setuptools.setup(
    name="osu-wiki-tools",
    version=VERSION,
    author="Walavouchey",
    author_email="wala@yui.tv",
    description="Various tools for osu! wiki contributors",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Walavouchey/osu-wiki-tools",
    project_urls={
        "Bug Tracker": "https://github.com/Walavouchey/osu-wiki-tools/issues"
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    test_suite="tests",
    packages=setuptools.find_packages(exclude=["tests", "tests.visual"]),
    entry_points={
        "console_scripts": [
            "osu-wiki-tools=wikitools_cli.osu_wiki_tools:console_main",
        ],
    },
    python_requires=">=3.11",
    install_requires=requirements,
)
