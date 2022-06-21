#!/usr/bin/env python3

"""
This script does the following:

1) Validates expiration hashes of the edited translations
2) Obtains directories of the modified en.md files, then lists translations in them which:
    * are not modified in the PR (assuming that the PR author took care of the rest), and
    * don't have the expiration markers/hashes

Alternatively, it can be run with {AUTOFIX_FLAG} (see the source below) to expire the translations automatically.
"""

import argparse
import fnmatch
import os
import subprocess as sp
import sys

from wikitools import article_parser, console, git_utils

# A pull request string which disables the check (has no effect here, listed for informational purposes only)
PULL_REQUEST_TAG = "SKIP_OUTDATED_CHECK"

# The front matter tag which means the translation needs to be updated
EXPIRED_TRANSLATION_TAG = "outdated_translation"

# The front matter tag which contains the commit hash since which the translation is not up to date
EXPIRATION_HASH_TAG = "outdated_since"

# The script flag which will automatically expire the translations
AUTOFIX_FLAG = "auto"


def print_translations_to_expire(*filenames, expiration_hash=None):
    print(f"{console.red('Error:')} You have edited some original articles (en.md), but did not outdate their translations:")
    print("\n".join(console.red(f"* {filename}") for filename in filenames))
    print(f"\nIf your changes DON'T NEED to be added to the translations, add {console.red(PULL_REQUEST_TAG)} anywhere in the description of your pull request.")
    print(
        f"Otherwise, rerun the script with {console.green('--' + AUTOFIX_FLAG)}, or "
        "add the following to each article's front matter (https://osu.ppy.sh/wiki/en/Article_styling_criteria/Formatting#front-matter):"
    )
    print()
    expiration_block = "" if expiration_hash is None else f"\n{EXPIRATION_HASH_TAG}: {expiration_hash}"
    front_matter = f"---{expiration_block}\n{EXPIRED_TRANSLATION_TAG}: true\n---"
    print(console.green(front_matter))


def print_bad_hash_error(*filenames, expiration_hash=None):
    print(
        "{} The following translations are incorrectly outdated (the {} hash is invalid){}".format(
            console.red("Error:"),
            console.red(EXPIRATION_HASH_TAG),
            "." if expiration_hash is None else ". Did you mean to use {} instead?".format(
                console.green(f"{EXPIRATION_HASH_TAG}: {expiration_hash}")
            )
        )
    )
    print("\n".join(console.red(f"* {filename}") for filename in filenames))


def parse_args(args):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-b", "--base-commit", required=True, help="commit since which to look for changes")
    parser.add_argument("-o", "--outdated-since", default="", help=f"commit hash for the {EXPIRATION_HASH_TAG} tag")
    parser.add_argument(f"--{AUTOFIX_FLAG}", default=False, action="store_true", help=f"automatically add `{EXPIRATION_HASH_TAG}: {{hash}}` to expired articles")
    return parser.parse_args(args)


def list_translations(modified_articles_dirs):
    """
    List ALL translations inside the folders of the modified articles.
    """

    for d in modified_articles_dirs:
        for filename in sorted(os.listdir(d)):
            if (
                filename == "en.md" or
                not (
                    fnmatch.fnmatch(filename, "??.md") or
                    fnmatch.fnmatch(filename, "??-??.md")
                )
            ):
                continue

            yield os.path.join(d, filename)


def list_expired_translations(all_translations, modified_translations):
    """
    List translations that are not touched by the changes and don't have the expiration tags (while they should).
    """

    for article_file in all_translations:
        if article_file in modified_translations:
            continue

        with open(article_file, "r") as fd:
            front_matter = article_parser.load_front_matter(fd)
        if EXPIRATION_HASH_TAG in front_matter or front_matter.get(EXPIRED_TRANSLATION_TAG, False):
            continue

        yield article_file


def list_modified_translations(base_commit):
    return set(git_utils.git_diff('wiki/**/*.md', ':(exclude)*/en.md', base_commit=base_commit))


def list_modified_originals(base_commit):
    return git_utils.git_diff('wiki/**/en.md', base_commit=base_commit)


def expire_translations(*translations, expiration_hash=""):
    """
    Write expiration hash and marker to several translations at once.
    """

    for article_file in translations:
        with open(article_file, "r") as fd:
            front_matter = article_parser.load_front_matter(fd)
        front_matter[EXPIRED_TRANSLATION_TAG] = True
        front_matter[EXPIRATION_HASH_TAG] = expiration_hash
        article_parser.save_front_matter(article_file, front_matter)


def check_commit_hashes(modified_translations):
    """
    Validate commit hashes using git show (check if they exist).
    """

    good_hashes, bad_hashes = set(), set()
    for article_file in modified_translations:
        with open(article_file, "r") as fd:
            front_matter = article_parser.load_front_matter(fd)
        expiration_hash = front_matter.get(EXPIRATION_HASH_TAG)
        if expiration_hash is None or expiration_hash in good_hashes:
            continue

        if expiration_hash in bad_hashes:
            yield article_file
            continue

        try:
            git_utils.git("show", expiration_hash, "--")
            good_hashes.add(expiration_hash)
        except RuntimeError:
            bad_hashes.add(expiration_hash)
            yield article_file


def main():
    args = parse_args(sys.argv[1:])
    exit_code = 0

    modified_translations = list_modified_translations(args.base_commit)
    with_bad_hashes = list(check_commit_hashes(modified_translations))
    if with_bad_hashes:
        print_bad_hash_error(*with_bad_hashes, expiration_hash=args.outdated_since or args.base_commit)
        print()
        exit_code = 1

    modified_originals = list_modified_originals(args.base_commit)
    if modified_originals:
        all_translations = list_translations(sorted(os.path.dirname(tl) for tl in modified_originals))
        translations_to_expire = list(list_expired_translations(all_translations, modified_translations))
        if translations_to_expire:
            # non-empty args.outdated_since => running on GitHub Action host
            expiration_hash = args.outdated_since or args.base_commit

            if getattr(args, AUTOFIX_FLAG, False):
                print(console.green('--{} detected, expiring the translations...'.format(AUTOFIX_FLAG)))
                expire_translations(*translations_to_expire, expiration_hash=expiration_hash)
                print(console.green('Done! To commit the changes, run:'))
                print(console.green('\tgit add {} && git commit -m "outdate translations"'.format(
                    " ".join(translations_to_expire)
                )))
            else:
                print_translations_to_expire(*translations_to_expire, expiration_hash=expiration_hash)
                exit_code = 1

        else:
            print(f"{console.grey('Notice:')} all unedited translations are properly outdated")

    else:
        print(f"{console.grey('Notice:')} no originals are edited, not going to check translations.")

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
