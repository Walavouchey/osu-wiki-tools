import os
import sys
import tempfile

import collections
import py
import pytest
import typing

import tests.utils as utils


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


class VisualTestCase(collections.namedtuple('VisualTestCase', 'description function')):
    description: str
    function: typing.Callable


class VisualTest(collections.namedtuple('VisualTest', 'name description cases')):
    name: str
    description: str
    cases: typing.List[VisualTestCase]
