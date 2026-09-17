#!/usr/bin/env python3
# noqa: EXE001
import argparse
import json
import sys
import typing

from wikitools import article_parser, console, file_utils, link_checker, redirect_parser
from wikitools.errors import (
    BrokenRedirectIdentifierError,
    LinkError,
    MissingIdentifierError,
)


def print_header(case_sensitive: bool):
    print(f"{console.red('Error:')} Some wiki or image links in the files you've changed have errors.\n")
    print("This can happen in one of the following ways:\n")
    print(
        "- The article or image that the link points to has since been moved or renamed" +
        (" (make sure to match capitalisation)" if case_sensitive else "")
    )
    print("- The link simply contains typos or formatting errors")
    print("- The link works, but contains locale selection (e.g. /wiki/en/Article_styling_criteria instead of /wiki/Article_styling_criteria)")
    print(
        "- The link works, but contains URL-escaped characters " +
        "(https://en.wikipedia.org/wiki/Percent-encoding). This only applies for links to articles and images inside the wiki."
    )
    print("- The link works, but incurs multiple redirects. Use a direct link instead.")
    print("\nFor more information on link style, see https://osu.ppy.sh/wiki/en/Article_styling_criteria/Formatting#links.")
    print(f"\nIf you need to bypass this check, add {console.red('SKIP_WIKILINK_CHECK')} anywhere in the PR description.\n")


def print_clean():
    print(f"{console.grey('Notice:')} No broken wiki or image links detected.", file=sys.stderr)


def s(i: int, s: str) -> str:
    return f"{i} {s}{'s' if i != 1 else ''}"


def print_count(errors: int, matches: int, error_files: int, files: int):
    print(f"{console.blue('Note:')} Found {s(errors, 'error')} in {s(error_files, 'file')} ({s(matches, 'link')} in {s(files, 'file')} checked).")


def highlight_links(s: str, errors: list[LinkError]) -> str:
    highlighted_line = ""
    prev_index = 0
    for error in errors:
        highlighted_line += s[prev_index: error.link.start]
        highlighted_line += error.pretty_link
        prev_index = error.link.end + 1
    highlighted_line += s[prev_index: -1]
    return highlighted_line


def print_errors(article: article_parser.Article, errors: dict[int, list[LinkError]], separate: bool, articles: dict[str, article_parser.Article]):
    if separate:
        for lineno, errors_on_line in sorted(errors.items()):
            for error in errors_on_line:
                print_errors(article, {lineno: [error]}, False, articles)
        return

    for lineno, errors_on_line in sorted(errors.items()):
        for error in errors_on_line:
            print(error.pretty_location(article.path, lineno))
        for error in errors_on_line:
            print(error.pretty())
            if isinstance(error, (MissingIdentifierError, BrokenRedirectIdentifierError)):
                suggestions = identifier_suggestions(error, articles)
                if suggestions:
                    print(
                        console.blue('Possible identifiers:') + "\n\t"
                        + "\n\t".join(
                            f"line {suggestion["lineno"]}: {suggestion["identifier"]}"
                            for suggestion in suggestions
                        )
                    )

        print()
        print(highlight_links(article.lines[lineno].raw_line, errors_on_line), end="\n\n")


ErrorList = list[tuple[article_parser.Article, dict[int, list[LinkError]]]]
FlatErrorList = list[tuple[article_parser.Article, int, int, LinkError]]


def errors_flattened(error_list: ErrorList) -> FlatErrorList:
    flat_error_list = []
    for article, errors in error_list:
        for lineno, errors_on_line in sorted(errors.items()):
            for error in errors_on_line:
                flat_error_list.append((article, lineno, error.pos, error))
    return flat_error_list


def errors_json(error_list: ErrorList, flatten: bool, articles: dict[str, article_parser.Article]) -> str:
    if flatten:
        flat_error_list = errors_flattened(error_list)

    if flatten:
        result = [
            {
                "path": article.path,
                "line": lineno,
                "column": error.pos,
                "link": error.link.raw_location,
                "type": "link-checker:" + error.id,
                "text": repr(error),
                "identifier_suggestions": identifier_suggestions(error, articles),
                "highlighted_line": highlight_links(article.lines[lineno].raw_line, [error]),
            }
            for article, lineno, column, error in flat_error_list
        ]
    else:
        result = [
            {
                "path": article.path,
                "lines_with_errors": [
                    {
                        "line": lineno,
                        "errors": [
                            {
                                "column": error.pos,
                                "link": error.link.raw_location,
                                "type": "link-checker:" + error.id,
                                "text": repr(error),
                                "possible_identifiers": identifier_suggestions(error, articles),
                                "highlighted_line": highlight_links(article.lines[lineno].raw_line, [error]),
                            }
                            for error in errors_on_line
                        ],
                    }
                    for lineno, errors_on_line in sorted(errors.items())
                ],
            }
            for article, errors in error_list
        ]

    return json.dumps(result)


def parse_args(args):
    parser = argparse.ArgumentParser(usage="%(prog)s check-links [options]")
    parser.add_argument("-t", "--target", nargs='*', help="paths to the articles you want to check, relative to the repository root")
    parser.add_argument("-a", "--all", action='store_true', help="check all articles")
    parser.add_argument("-s", "--separate", action='store_true', help="print errors that appear on the same line separately")
    parser.add_argument("-f", "--format", choices=["regular", "json", "github"], default="regular", help="specify output format")

    parser.add_argument(
        "--in-outdated-articles",
        action='store_true',
        help="check links in outdated articles or translations"
    )
    parser.add_argument(
        "--to-sections-in-outdated-translations",
        action='store_true',
        help="check section links in translations that point to outdated translations of the same language"
    )
    parser.add_argument(
        "--to-sections-in-missing-translations",
        action='store_true',
        help="check section links in translations that point to articles with no available translations of the same language"
    )

    parser.add_argument("--case-sensitive", action='store_true', help="check file existence case-sensitively")

    parser.add_argument("-r", "--root", help="specify repository root, current working directory assumed otherwise")
    return parser.parse_args(args)


def identifier_suggestions(error: LinkError, articles: dict[str, article_parser.Article]):
    if isinstance(error, (MissingIdentifierError, BrokenRedirectIdentifierError)):
        return [
            {
                "lineno": lineno,
                "identifier": identifier
            }
            for identifier, lineno in sorted(articles[error.path].identifiers.items(), key=lambda tuple_: tuple_[1])
        ]


def filter_errors(
    filter_function: typing.Callable[[LinkError], dict[int, list[LinkError]]],
    errors: dict[int, list[LinkError]]
) -> dict[int, list[LinkError]]:
    return {
        a: b for a, b in {
            i: [
                e for e in errors_on_line if filter_function(e)
            ]
            for i, errors_on_line in errors.items()
        }.items()
        if b
    }


def main(*args):
    args = parse_args(args)
    if not args.target and not args.all:
        print(f"{console.grey('Notice:')} No articles to check.")
        sys.exit(0)

    if args.root:
        changed_cwd = file_utils.ChangeDirectory(args.root)  # Keep alive to maintain directory change

    filenames = []
    if args.all:
        filenames = file_utils.list_all_articles_and_newsposts()
    else:
        filenames = list(filter(lambda x: file_utils.is_article(x) or file_utils.is_newspost(x), args.target))

    redirects = redirect_parser.load_redirects("wiki/redirect.yaml")

    articles = {}
    for filename in filenames:
        a = article_parser.parse(filename)
        articles[a.path] = a

    exit_code = 0
    all_errors = []
    error_count = 0
    link_count = 0
    error_file_count = 0
    file_count = 0

    for _, article in sorted(articles.items()):
        if not args.in_outdated_articles and (article.front_matter.get("outdated", False) or article.front_matter.get("outdated_translation", False)):
            continue

        link_count += sum(len(_.links) for _ in article.lines.values())
        file_count += 1

        errors = link_checker.check_article(article, redirects, articles, args.case_sensitive)

        if not args.to_sections_in_outdated_translations:
            errors = filter_errors(
                lambda e: not ((isinstance(e, (MissingIdentifierError, BrokenRedirectIdentifierError))) and
                               e.translation_outdated), errors)

        if not args.to_sections_in_missing_translations:
            errors = filter_errors(
                lambda e: not ((isinstance(e, (MissingIdentifierError, BrokenRedirectIdentifierError))) and
                               e.no_translation_available), errors)

        if not errors:
            continue

        error_file_count += 1
        error_count += sum(len(e) for e in errors.values())
        exit_code = 1

        all_errors.append((article, errors))

    if exit_code == 0:
        print_clean()
        return exit_code

    match args.format:
        case "regular":
            print_header(args.case_sensitive)

            for article, errors in all_errors:
                print_errors(article, errors, args.separate, articles)

            print_count(error_count, link_count, error_file_count, file_count)

        case "json":
            print(errors_json(all_errors, args.separate, articles))

        case "github":
            print("::group::Annotations")
            for article, lineno, column, error in errors_flattened(all_errors)[:10]:
                print("::error file={},line={},col={},title={}::{}".format(
                    article.path,
                    lineno,
                    column,
                    "link-checker:" + error.id,
                    repr(error),
                ))
            print("::endgroup::\n")

            print_header(args.case_sensitive)

            for article, errors in all_errors:
                print_errors(article, errors, args.separate, articles)

            print_count(error_count, link_count, error_file_count, file_count)

    if args.root:
        del changed_cwd
    return exit_code


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
