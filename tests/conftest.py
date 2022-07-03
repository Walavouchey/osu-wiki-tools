import os
import sys

import collections
import py
import pytest
import typing


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


class VisualTestCase(collections.namedtuple('VisualTestCase', 'description function')):
    description: str
    function: typing.Callable


class VisualTest(collections.namedtuple('VisualTest', 'name description cases')):
    name: str
    description: str
    cases: typing.List[VisualTestCase]
