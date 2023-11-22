import collections
import os

import py

from wikitools import git_utils


def create_files(root: py.path.local, *articles):
    for path, contents in articles:
        article_folder = root.join(os.path.dirname(path))
        article_folder.ensure(dir=1)
        if type(contents) == bytes:
            article_folder.join(os.path.basename(path)).write_binary(contents)
        else:
            article_folder.join(os.path.basename(path)).write_text(contents, encoding='utf-8')


def stage_all_and_commit(commit_message):
    git_utils.git("add", ".")
    git_utils.git("commit", "-m", commit_message)


def set_up_dummy_repo():
    git_utils.git("init")
    git_utils.git("config", "user.name", "John Smith")
    git_utils.git("config", "user.email", "john.smith@example.com")
    git_utils.git("config", "commit.gpgsign", "false")


def get_changed_files():
    return git_utils.git("diff", "--diff-filter=d", "--name-only").splitlines()


def get_last_commit_hash():
    return git_utils.git("show", "HEAD", "--pretty=format:%H", "-s")


def take(the_list, *may_contain):
    return list(filter(lambda item : any(thing in item for thing in may_contain), the_list))


def remove(the_list, *may_not_contain):
    return list(filter(lambda item : all(thing not in item for thing in may_not_contain), the_list))
