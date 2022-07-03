import fnmatch
import os
import typing


class ChangeDirectory:
    cwd: str

    def __init__(self, repo_root: str):
        self.cwd = os.getcwd()
        os.chdir(repo_root)

    def __del__(self):
        os.chdir(self.cwd)


def is_newspost(path: str) -> bool:
    return (
        os.path.dirname(path).endswith("news") and
        path.endswith(".md")
    )


def is_article(path: str) -> bool:
    filename = os.path.basename(path)
    return (
        fnmatch.fnmatch(filename, "??.md") or
        fnmatch.fnmatch(filename, "??-??.md")
    )


def is_translation(path: str) -> bool:
    filename = os.path.basename(path)
    return (
        filename != "en.md" and
        (
            fnmatch.fnmatch(filename, "??.md") or
            fnmatch.fnmatch(filename, "??-??.md")
        )
    )


def is_original(path: str) -> bool:
    return os.path.basename(path) == "en.md"


def list_all_files(roots: typing.Iterable[str]=["wiki"]) -> typing.Generator[str, None, None]:
    for item in roots:
        for root, _, filenames in os.walk(item):
            for f in filenames:
                filepath = os.path.join(root, f)
                yield filepath


def list_all_article_dirs() -> typing.Generator[str, None, None]:
    """
    List ALL article directories in the wiki
    """

    for root, _, filenames in os.walk("wiki"):
        if any(is_article(f) for f in filenames):
            yield root


def list_all_articles() -> typing.Generator[str, None, None]:
    """
    List ALL article files in the wiki
    """

    for filepath in list_all_files(["wiki"]):
        if is_article(filepath):
            yield filepath


def list_all_newsposts() -> typing.Generator[str, None, None]:
    """
    List ALL newsposts
    """

    for filepath in list_all_files(["news"]):
        if is_newspost(filepath):
            yield filepath


def list_all_articles_and_newsposts() -> typing.Generator[str, None, None]:
    """
    List ALL article and newspost files 
    """

    for filepath in list_all_files(["wiki", "news"]):
        if is_article(filepath) or is_newspost(filepath):
            yield filepath


def list_all_translations(article_dirs: typing.Iterable[str]) -> typing.Generator[str, None, None]:
    """
    List ALL translations inside the articles specified
    """

    for d in article_dirs:
        for filename in sorted(os.listdir(d)):
            if is_original(filename) or not is_article(filename):
                continue

            yield os.path.join(d, filename).replace("\\", "/")
