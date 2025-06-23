#!/usr/bin/env python3

"""
This script does the following:

1) Validates commit hashes of edited outdated translations (or all translations with --all)
2) Obtains directories of the modified en.md files, then lists translations in them which:
    * are not modified in the PR (assuming that the PR author took care of the rest), and
    * don't have the outdated markers/hashes

Alternatively, it can be run with --autofix (and --autocommit, or just -fc) to outdate the translations automatically.
"""

import argparse
import fnmatch
import itertools
import os
import os.path
import sys

from wikitools import article_parser, console, git_utils, file_utils

import braceexpand

# A pull request string which disables the check (has no effect here, listed for informational purposes only)
PULL_REQUEST_TAG = "SKIP_OUTDATED_CHECK"

# The front matter tag which means the translation needs to be updated
OUTDATED_TRANSLATION_TAG = "outdated_translation"

# The front matter tag which contains the commit hash since which the translation is not up to date
OUTDATED_HASH_TAG = "outdated_since"

# The script flag which will automatically outdate translations
AUTOFIX_FLAG = "--autofix"
AUTOFIX_FLAG_SHORT = "-f"

# The script flag which will automatically commit changes
AUTOCOMMIT_FLAG = "--autocommit"
AUTOCOMMIT_FLAG_SHORT = "-c"


def print_translations_to_outdate(*filenames, outdated_hash=None, no_recommend_autofix=False):
    print(f"{console.red('Error:')} You have edited some original articles (en.md), but did not outdate their translations:")
    print("\n".join(console.red(f"* {filename}") for filename in filenames))
    print(f"\nIf your changes DON'T NEED to be added to the translations, add {console.red(PULL_REQUEST_TAG)} anywhere in the description of your pull request.")
    if not no_recommend_autofix:
        print(
            f"Otherwise, rerun the script with {console.green(AUTOFIX_FLAG)} (and perhaps {console.green(AUTOCOMMIT_FLAG)}), or "
            "add the following to each article's front matter (https://osu.ppy.sh/wiki/en/Article_styling_criteria/Formatting#front-matter):"
        )
    else:
        print(
            "Otherwise, add the following to each article's front matter "
            "(https://osu.ppy.sh/wiki/en/Article_styling_criteria/Formatting#front-matter):"
        )
    print()
    outdated_block = "" if outdated_hash is None else f"\n{OUTDATED_HASH_TAG}: {outdated_hash}"
    front_matter = f"---{outdated_block}\n{OUTDATED_TRANSLATION_TAG}: true\n---"

    # the seemingly needless complication here ensures that the github action log displays all three lines in colour
    print("\n".join([console.green(line) for line in front_matter.split("\n")]))


def print_bad_hash_error(*filenames, outdated_hash=None):
    print(
        "{} The following translations are incorrectly outdated (the {} hash is invalid).{}".format(
            console.red("Error:"),
            console.red(OUTDATED_HASH_TAG),
            "" if outdated_hash is None else " Did you mean to use {} instead?".format(
                console.green("{}: {}".format(OUTDATED_HASH_TAG, outdated_hash))
            )
        )
    )
    print("\n".join(console.red(f"* {filename}") for filename in filenames))


def parse_args(args):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter, usage="%(prog)s check-outdated-articles [options]")
    parser.add_argument("-b", "--base-commit", default="master", help="commit since which to look for changes")
    parser.add_argument("-o", "--outdated-since", help=f"commit hash for the {OUTDATED_HASH_TAG} tag, uses the first commit where HEAD diverged from master if unspecified")
    parser.add_argument("-a", "--all", default=False, action="store_true", help="look for incorrect hashes in all outdated articles")
    parser.add_argument(f"{AUTOFIX_FLAG_SHORT}", f"{AUTOFIX_FLAG}", default=False, action="store_true", help=f"automatically add `{OUTDATED_HASH_TAG}: {{hash}}` to outdated articles")
    parser.add_argument(f"{AUTOCOMMIT_FLAG_SHORT}", f"{AUTOCOMMIT_FLAG}", default=False, action="store_true", help="automatically commit changes")
    parser.add_argument("-r", "--root", help="specify repository root, current working directory assumed otherwise")
    parser.add_argument("-e", "--exclude", action='append', help="list of paths to exclude from checking (accepts file paths, directories, and shell patterns)")
    parser.add_argument("--no-recommend-autofix", action='store_true', help=f"don't recommend rerunning the script with {AUTOFIX_FLAG}")
    return parser.parse_args(args)


def list_outdated_translations(all_translations, modified_translations):
    """
    List translations that are not touched by the changes and don't have the outdated tags (while they should).
    """

    for article_file in all_translations:
        if article_file in modified_translations:
            continue

        with open(article_file, "r", encoding='utf-8') as fd:
            front_matter = article_parser.load_front_matter(fd)
        if OUTDATED_HASH_TAG in front_matter or front_matter.get(OUTDATED_TRANSLATION_TAG, False):
            continue

        yield article_file


def list_modified_translations(base_commit):
    return filter(file_utils.is_translation, git_utils.git_diff('wiki/**/*.md', base_commit=base_commit))


def list_modified_originals(base_commit):
    return git_utils.git_diff('wiki/**/en.md', base_commit=base_commit)


def outdate_translations(*translations, outdated_hash):
    """
    Write outdated hash and marker to several translations at once.
    """

    for article_file in translations:
        with open(article_file, "r", encoding='utf-8') as fd:
            front_matter = article_parser.load_front_matter(fd)
        front_matter[OUTDATED_TRANSLATION_TAG] = True
        front_matter[OUTDATED_HASH_TAG] = outdated_hash
        article_parser.save_front_matter(article_file, front_matter)


def check_commit_hashes(modified_translations):
    """
    Validate commit hashes by checking if git has an associated object.
    """

    good_hashes, bad_hashes = set(), set()
    for article_file in modified_translations:
        with open(article_file, "r", encoding='utf-8') as fd:
            front_matter = article_parser.load_front_matter(fd)
        outdated_hash = front_matter.get(OUTDATED_HASH_TAG)
        if outdated_hash is None or outdated_hash in good_hashes:
            continue

        if outdated_hash in bad_hashes:
            yield article_file
            continue

        try:
            git_utils.git("cat-file", "-e", f"{outdated_hash}^{{commit}}")
            good_hashes.add(outdated_hash)
        except RuntimeError:
            bad_hashes.add(outdated_hash)
            yield article_file


def path_match(file_path: str, patterns: list[str]) -> bool:
    """
    Check if a file path matches one or more patterns that exclude it from the outdated check.

    Patterns may look like this, with the wiki/ prefix optionally omitted:

      - Individual articles: wiki/Path/To/Article/en.md
      - Article directories: wiki/Article
      - Fnmatch masks: wiki/*/es.md
      - Paths with shell-style brace expansion:
        - wiki/{Article,Other_article}/es.md
        - wiki/{Article,Other_article}/{es,jp}.md
    """

    for article_path in [file_path, file_path.removeprefix("wiki/")]:
        for path_or_mask in patterns:
            if (
                article_path == path_or_mask
                or os.path.commonpath((article_path, path_or_mask)).replace("\\", "/") == path_or_mask
                or fnmatch.fnmatch(article_path, path_or_mask)
            ):
                return True
    return False


def main(*args):
    args = parse_args(args)
    exit_code = 0

    if args.root:
        changed_cwd = file_utils.ChangeDirectory(args.root)  # Keep alive to maintain directory change  # noqa: F841

    modified_translations = set()
    with_bad_hashes = list()

    if args.all:
        all_translations = file_utils.list_all_translations(file_utils.list_all_article_dirs())
        with_bad_hashes = list(check_commit_hashes(all_translations))
    else:
        modified_translations = set(list_modified_translations(args.base_commit))
        with_bad_hashes = list(check_commit_hashes(modified_translations))

    outdated_hash = None

    if with_bad_hashes:
        outdated_hash = args.outdated_since or git_utils.get_first_branch_commit()
        print_bad_hash_error(*with_bad_hashes, outdated_hash=outdated_hash)
        print()
        exit_code = 1

    modified_originals = list_modified_originals(args.base_commit)
    if modified_originals:
        all_translations = file_utils.list_all_translations(sorted(os.path.dirname(tl) for tl in modified_originals))
        temp_translations_to_outdate = list(list_outdated_translations(all_translations, modified_translations))

        translations_to_outdate = []
        if args.exclude:
            excluded_count = 0
            masks = list(itertools.chain(*map(
                lambda single_argument: list(braceexpand.braceexpand(single_argument)),
                args.exclude
            )))

            for translation in temp_translations_to_outdate:
                if path_match(translation, masks):
                    excluded_count += 1
                else:
                    translations_to_outdate.append(translation)
            print(f"{excluded_count} of {len(temp_translations_to_outdate)} translation(s) skipped due to --exclude")
        else:
            translations_to_outdate = temp_translations_to_outdate

        if translations_to_outdate:
            outdated_hash = outdated_hash or args.outdated_since or git_utils.get_first_branch_commit()

            should_autofix = getattr(args, AUTOFIX_FLAG[2:], False)
            should_autocommit = getattr(args, AUTOCOMMIT_FLAG[2:], False)
            if should_autofix:
                print(console.green('{} specified, outdating translations...'.format(AUTOFIX_FLAG)))

                if outdated_hash:
                    outdate_translations(*translations_to_outdate, outdated_hash=outdated_hash)
                    if not should_autocommit:
                        print(console.green('Done! To commit the changes, run:'))
                        print(console.green('\tgit add {}; git commit -m "outdate translations"'.format(
                            " ".join(translations_to_outdate)
                        )))
                    else:
                        print(console.green('{} specified, committing changes...'.format(AUTOCOMMIT_FLAG)))
                        git_utils.git("add", *translations_to_outdate)
                        git_utils.git("commit", "-m", "outdate translations")
                        print(console.green('Done! The changes have been committed for you.'))
                        print()
                        print(git_utils.git("show", "HEAD", "--no-patch"))
                        print("Changed files:")
                        for file_path in translations_to_outdate:
                            print(console.green(f"* {file_path}"))
                else:
                    print(f"{console.red('Error:')} --outdated-since was not specified and HEAD has not diverged from master.")
                    exit_code = 1
            else:
                print_translations_to_outdate(*translations_to_outdate, outdated_hash=outdated_hash, no_recommend_autofix=args.no_recommend_autofix)
                exit_code = 1

        else:
            print(f"{console.grey('Notice:')} all unedited translations are properly outdated.")

    else:
        print(f"{console.grey('Notice:')} no originals are edited, not going to check translations.")

    if args.root:
        del changed_cwd
    return exit_code


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
