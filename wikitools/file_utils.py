import fnmatch
import itertools
import os
import typing
import pathlib


class ChangeDirectory:
    cwd: str

    def __init__(self, repo_root: str):
        self.cwd = os.getcwd()
        os.chdir(repo_root)

    def __del__(self):
        os.chdir(self.cwd)


def normalised(path: str) -> str:
    normalised = os.path.normpath(path).replace("\\", "/")
    if normalised.startswith("./"):
        normalised = normalised[2:]
    return normalised


def exists_case_sensitive(path: pathlib.Path):
    """
    Case-sensitive file/directory existence check
    """

    if os.name == 'nt':
        try:
            path_string = path.as_posix()
            # windows disallows two files that differ only in casing, so there are no special considerations for that
            return normalised(path_string) == normalised(os.path.relpath(os.path.realpath(path_string, strict=True)))
        except OSError:
            return False
    else:
        return path.exists()


def exists_case_insensitive(path: pathlib.Path):
    """
    Case-insensitive file/diretory existence check
    """

    if os.name == 'nt':
        return path.exists()
    else:
        # case-insensitive directory/file existence checking isn't trivial in case-sensitive file systems. some caching is needed
        if not hasattr(exists_case_insensitive, 'all_article_paths_lowercased'):
            article_set = set(normalised(article_path.lower()) for article_path in itertools.chain(list_all_articles_and_newsposts(), list_all_article_dirs()))
            setattr(exists_case_insensitive, 'all_article_paths_lowercased', article_set)
        all_article_paths_lowercased = getattr(exists_case_insensitive, 'all_article_paths_lowercased')

        return normalised(os.path.relpath(path.as_posix()).lower()) in all_article_paths_lowercased


def is_newspost(path: str) -> bool:
    return (
        normalised(os.path.dirname(path)).startswith("news") and
        path.endswith(".md")
    )


def is_article(path: str) -> bool:
    filename = os.path.basename(path)
    return (
        fnmatch.fnmatch(filename, "??.md") or
        fnmatch.fnmatch(filename, "???.md") or
        fnmatch.fnmatch(filename, "??-??.md")
    )


def is_translation(path: str) -> bool:
    filename = os.path.basename(path)
    return (
        filename != "en.md" and
        (
            fnmatch.fnmatch(filename, "??.md") or
            fnmatch.fnmatch(filename, "???.md") or
            fnmatch.fnmatch(filename, "??-??.md")
        )
    )


def is_original(path: str) -> bool:
    return os.path.basename(path) == "en.md"


def list_all_files(roots: typing.Iterable[str]=["wiki"]) -> typing.Generator[str, None, None]:
    for item in roots:
        for root, _, filenames in os.walk(item):
            for f in filenames:
                filepath = os.path.join(root, f).replace("\\", "/")
                yield filepath


def list_all_article_dirs() -> typing.Generator[str, None, None]:
    """
    List ALL article directories in the wiki
    """

    for root, _, filenames in os.walk("wiki"):
        if any(is_article(f) for f in filenames):
            yield root.replace("\\", "/")


def list_all_articles() -> typing.Generator[str, None, None]:
    """
    List ALL article files in the wiki
    """

    for filepath in list_all_files(["wiki"]):
        if is_article(filepath):
            yield filepath.replace("\\", "/")


def list_all_newsposts() -> typing.Generator[str, None, None]:
    """
    List ALL newsposts
    """

    for filepath in list_all_files(["news"]):
        if is_newspost(filepath):
            yield filepath.replace("\\", "/")


def list_all_articles_and_newsposts() -> typing.Generator[str, None, None]:
    """
    List ALL article and newspost files 
    """

    for filepath in list_all_files(["wiki", "news"]):
        if is_article(filepath) or is_newspost(filepath):
            yield filepath.replace("\\", "/")


def list_all_translations(article_dirs: typing.Iterable[str]) -> typing.Generator[str, None, None]:
    """
    List ALL translations inside the articles specified
    """

    for d in article_dirs:
        for filename in sorted(os.listdir(d)):
            if is_original(filename) or not is_article(filename):
                continue

            yield os.path.join(d, filename).replace("\\", "/")
