import os
import sys

import py
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope='function')
def root(tmpdir: py.path.local):
    wiki = tmpdir.join('wiki')
    news = tmpdir.join('news')
    wiki.mkdir()
    news.mkdir()

    # XXX(TicClick): this is a hack, since most functions expect the 'wiki' directory is in our sight.
    # when the --root flag is added, this may be changed
    curdir = os.getcwd()
    os.chdir(tmpdir)
    yield tmpdir
    os.chdir(curdir)
