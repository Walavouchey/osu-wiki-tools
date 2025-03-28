#!/usr/bin/env python3

import argparse
import sys
import typing
from pathlib import Path

from wikitools import console, errors as error_types, file_utils
from wikitools.file_utils import exists_case_sensitive


def print_clean():
    print("Notice: No file or folder structure errors detected.")


def s(i: int, s: str) -> str:
    return f"{i} {s}{'s' if i != 1 else ''}"


def print_count(errors: int, files: int):
    print(f"{console.blue('Note:')} Found {s(errors, 'error')} ({s(files, 'file')} checked).")


def check_missing_english_version(file_path: Path) -> typing.Optional[error_types.MissingEnglishVersionError]:
    path = Path(file_path)
    dir_name = path.parent
    english_path = dir_name / "en.md"
    if not exists_case_sensitive(english_path):
        return error_types.MissingEnglishVersionError(file_path)

    return None


def parse_args(args):
    parser = argparse.ArgumentParser(usage="%(prog)s check-files [options]")
    parser.add_argument("-t", "--target", nargs='*', help="paths to the articles you want to check, relative to the repository root")
    parser.add_argument("-a", "--all", action='store_true', help="check all articles")


    parser.add_argument("-r", "--root", help="specify repository root, current working directory assumed otherwise")
    return parser.parse_args(args)


def main(*args):
    args = parse_args(args)
    if not args.target and not args.all:
        print(f"{console.grey('Notice:')} No articles to check.")
        sys.exit(0)

    if args.root:
        changed_cwd = file_utils.ChangeDirectory(args.root)

    filenames = []
    if args.all:
        filenames = file_utils.list_all_articles()
    else:
        filenames = list(filter(lambda x: file_utils.is_article(x) or file_utils.is_newspost(x), args.target))

    exit_code = 0

    error_count = 0
    file_count = 0

    for filename in filenames:
        file_count += 1
        maybe_error = check_missing_english_version(filename)
        if maybe_error:
            exit_code = 1
            error_count += 1
            print(maybe_error.pretty_location())
            print(maybe_error.pretty())
            print()

    if exit_code == 0:
        print_clean()
    else:
        print_count(error_count, file_count)

    if args.root:
        del changed_cwd
    return exit_code


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
