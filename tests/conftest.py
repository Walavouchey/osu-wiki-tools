import os
import sys
import tempfile

import collections
import importlib
import pkgutil
import py
import pytest
import typing

import tests.utils as utils
import tests.visual

from wikitools import console


sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope='function')
def root(tmpdir: py.path.local):
    wiki = tmpdir.join('wiki')
    news = tmpdir.join('news')
    wiki.mkdir()
    news.mkdir()

    curdir = os.getcwd()
    os.chdir(tmpdir)
    yield tmpdir
    os.chdir(curdir)


class DummyRepository():
    """
    The same exact thing as above but the poor man's non-pytest version (for visual tests)

    Usage:
        with DummyRepository() as root:
            # do stuff
        # automatically cleaned up when finished
    """

    def __init__(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.curdir = os.getcwd()
        os.chdir(self.tmpdir.name)
        utils.set_up_dummy_repo()

    def __enter__(self):
        return py.path.local(self.tmpdir.name)

    def __exit__(self, exc, value, tb):
        os.chdir(self.curdir)
        del self.curdir
        del self.tmpdir


class VisualTestCase(collections.namedtuple('VisualTestCase', 'name description function')):
    name: str
    description: str
    function: typing.Callable


class VisualTest(collections.namedtuple('VisualTest', 'name description cases')):
    name: str
    description: str
    cases: typing.List[VisualTestCase]


def get_visual_tests():
    return [
        importlib.import_module(module).test for module in
        (
            module for _, module, _ in pkgutil.walk_packages(
                path=tests.visual.__path__,
                prefix=tests.visual.__name__ + '.',
                onerror=lambda _: None
            )
        )
        if "conftest" not in module
    ]


def run_visual_test(tests, test_index, case_index):
    test = tests[test_index]
    print(f"({test_index + 1}/{len(tests)})", console.red(test.name), "-", test.description)
    test_case = test.cases[case_index]
    print()
    print(f"- ({case_index + 1}/{len(test.cases)})", console.blue(test_case.description))
    print()
    try:
        test_case.function()
    except SystemExit as e:
        print()
        print(f"Program exited with {console.red(e.code) if e.code != 0 else console.green(e.code)}")
        assert e.code == 0
