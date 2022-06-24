# type: ignore
import setuptools

with open("README.md", "r", encoding="utf-8") as fd:
    long_description = fd.read()

setuptools.setup(
    name="osu-wiki-tools",
    version="0.0.3",
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
    packages=setuptools.find_packages(),
    entry_points={
        "console_scripts": [
            "find-broken-wikilinks=wikitools_cli.find_broken_wikilinks:main",
            "check-outdated-articles=wikitools_cli.check_outdated_articles:console_main",
        ],
    },
    python_requires=">=3.10",
)
