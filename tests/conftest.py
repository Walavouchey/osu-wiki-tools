import os
import sys

import py
import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope='function')
def root(tmpdir: py.path.local):
    root = tmpdir.join('wiki')
    root.mkdir()

    # XXX(TicClick): this is a hack, since most functions expect the 'wiki' directory is in our sight.
    # when the --root flag is added, this may be changed
    curdir = os.getcwd()
    os.chdir(tmpdir)
    yield root
    os.chdir(curdir)
