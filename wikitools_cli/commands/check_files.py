#!/usr/bin/env python3

import argparse
import sys
import typing
from pathlib import Path
import json

from wikitools import console, errors as error_types, file_utils
from wikitools.file_utils import exists_case_sensitive


def print_error(error: error_types.FileError):
    print(error.pretty_location())
    print(error.pretty())
    print()


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


def files_deduplicated(file_paths: typing.List[Path]) -> typing.List[Path]:
    seen = set()
    deduplicated = []
    for file in sorted(file_paths):
        dir = file.parent
        if dir not in seen:
            deduplicated.append(file)
            seen.add(dir)
    return deduplicated


def errors_json(errors: typing.List[error_types.FileError]) -> str:
    return json.dumps(
        [
            {
                "path": error.path.as_posix(),
                "type": "file-checker:" + error.id,
                "text": repr(error),
            }
            for error in errors
        ]
    )


def parse_args(args):
    parser = argparse.ArgumentParser(usage="%(prog)s check-files [options]")
    parser.add_argument("-t", "--target", nargs='*', help="paths to the articles you want to check, relative to the repository root")
    parser.add_argument("-a", "--all", action='store_true', help="check all articles")
    parser.add_argument("-f", "--format", choices=["regular", "json", "github"], default="regular", help="specify output format")
    parser.add_argument("-r", "--root", help="specify repository root, current working directory assumed otherwise")
    return parser.parse_args(args)


def main(*args):
    args = parse_args(args)
    if not args.target and not args.all:
        print(f"{console.grey('Notice:')} No articles to check.")
        sys.exit(0)

    if args.root:
        changed_cwd = file_utils.ChangeDirectory(args.root)  # Keep alive to maintain directory change  # noqa: F841

    if args.all:
        filenames = file_utils.list_all_articles()
    else:
        filenames = list(filter(lambda x: file_utils.is_article(x) or file_utils.is_newspost(x), args.target))

    exit_code = 0
    error_count = 0
    file_count = 0
    all_errors = []

    for filename in files_deduplicated([Path(f) for f in filenames]):
        file_count += 1

        error = check_missing_english_version(filename)

        if error:
            exit_code = 1
            error_count += 1
            all_errors.append(error)

    if exit_code == 0:
        print_clean()
        return exit_code

    match args.format:
        case "regular":
            for error in all_errors:
                print_error(error)

            print_count(error_count, file_count)

        case "json":
            print(errors_json(all_errors))

        case "github":
            print("::group::Annotations")
            for error in all_errors[:10]:
                print(f"::error file={error.file},title={"file-checker:" + error.id}::{repr(error)}")
            print("::endgroup::\n")

            for error in all_errors:
                print_error(error)

            print_count(error_count, file_count)

    if args.root:
        del changed_cwd
    return exit_code


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
