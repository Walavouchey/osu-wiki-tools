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


def create_files(root: py.path.local, *articles):
    for path, contents in articles:
        article_folder = root.join(os.path.dirname(path))
        article_folder.ensure(dir=1)
        article_folder.join(os.path.basename(path)).write_text(contents, encoding='utf-8')
