import fnmatch
import os

def is_article(path):
    filename = os.path.basename(path)
    return (
        fnmatch.fnmatch(filename, "??.md") or
        fnmatch.fnmatch(filename, "??-??.md")
    )


def is_translation(path):
    filename = os.path.basename(path)
    return (
        filename != "en.md" and
        (
            fnmatch.fnmatch(filename, "??.md") or
            fnmatch.fnmatch(filename, "??-??.md")
        )
    )


def is_original(path):
    return os.path.basename(path) == "en.md"


def list_all_files(roots=["wiki"]):
    for item in roots:
        if os.path.isdir(item):
            for root, _, filenames in os.walk(item):
                for f in filenames:
                    filepath = os.path.join(root, f)
                    yield filepath
        elif os.path.isfile(item):
            yield item


def list_all_article_dirs():
    """
    List ALL article directories in the wiki
    """

    for root, _, filenames in os.walk("wiki"):
        if any(is_article(f) for f in filenames):
            yield root


def list_all_article_files():
    """
    List ALL article files in the wiki
    """

    for root, _, filenames in os.walk("wiki"):
        for f in filenames:
            filepath = os.path.join(root, f)
            if is_article(filepath):
                yield filepath


def list_all_translations(article_dirs):
    """
    List ALL translations inside the articles specified
    """

    for d in article_dirs:
        for filename in sorted(os.listdir(d)):
            if is_original(filename) or not is_article(filename):
                continue

            yield os.path.join(d, filename).replace("\\", "/")
