#!/usr/bin/env python3

import argparse
import sys
import typing
import json
from itertools import chain, islice

from wikitools import article_parser, console, link_checker, redirect_parser, errors as error_types, file_utils


def print_error(case_sensitive: bool):
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
    print("Notice: No broken wiki or image links detected.")


def s(i: int, s: str) -> str:
    return f"{i} {s}{'s' if i != 1 else ''}"


def print_count(errors: int, matches: int, error_files: int, files: int):
    print(f"{console.blue('Note:')} Found {s(errors, 'error')} in {s(error_files, 'file')} ({s(matches, 'link')} in {s(files, 'file')} checked).")


def highlight_links(s: str, errors: typing.List[error_types.LinkError]) -> str:
    highlighted_line = ""
    prev_index = 0
    for error in errors:
        highlighted_line += s[prev_index: error.link.start]
        highlighted_line += error.pretty_link
        prev_index = error.link.end + 1
    highlighted_line += s[prev_index: -1]
    return highlighted_line


def print_errors(errors: typing.Dict[int, typing.List[error_types.LinkError]], article: article_parser.Article, separate: bool):
    for lineno, errors_on_line in sorted(errors.items()):
        for e in errors_on_line:
            print(e.pretty_location(article.path, lineno))
        for e in errors_on_line:
            print(e.pretty())
            if isinstance(e, error_types.MissingIdentifierError) or isinstance(e, error_types.BrokenRedirectIdentifierError):
                suggestions = identifier_suggestions(e, article)
                if suggestions:
                    print('{}\n\t{}'.format(console.blue('Suggestions:'), suggestions))

        print()
        if separate:
            for e in errors_on_line:
                print(highlight_links(article.lines[lineno].raw_line, [e]), end="\n\n")
        else:
            print(highlight_links(article.lines[lineno].raw_line, errors_on_line), end="\n\n")


def identifier_suggestions_json(e: error_types.LinkError, article: article_parser.Article):
    if isinstance(e, error_types.MissingIdentifierError) or isinstance(e, error_types.BrokenRedirectIdentifierError):
        return [
            {
                "lineno": lineno,
                "identifier": identifier
            }
            for identifier, lineno in sorted(article.identifiers.items(), key=lambda tuple_: tuple_[1])
        ]


def error_json(errors: typing.Dict[int, typing.List[error_types.LinkError]], article: article_parser.Article, separate: bool):
    if separate:
        error_list = []
        for lineno, errors_on_line in sorted(errors.items()):
            for error in errors_on_line:
                error_list.append((lineno, [error]))
    else:
        error_list = sorted(errors.items())

    if separate:
        return [
            {
                "path": article.path,
                "lineno": lineno,
                "column": e[0].pos,
                "link": e[0].link.colourise_location(fragment_only=e[0]._colourise_fragment_only),
                "type": type(e[0]).__name__,
                "text": repr(e[0]),
                "identifier_suggestions": identifier_suggestions_json(e[0], article),
                "highlighted_line": highlight_links(article.lines[lineno].raw_line, errors_on_line),
            }
            for lineno, e in error_list
        ]
    else:
        return {
            "path": article.path,
            "lines_with_errors": [
                {
                    "lineno": lineno,
                    "errors": [
                        {
                            "column": e.pos,
                            "link": e.link.colourise_location(fragment_only=e._colourise_fragment_only),
                            "type": type(e).__name__,
                            "text": repr(e),
                            "identifier_suggestions": identifier_suggestions_json(e, article),
                            "highlighted_line": highlight_links(article.lines[lineno].raw_line, [e]),
                        }
                        for e in errors_on_line
                    ],
                }
                for lineno, errors_on_line in error_list
            ],
        }


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


def identifier_suggestions(e, articles):
    return '\n\t'.join((
        'line {}: {}'.format(lineno, identifier)
        for identifier, lineno in sorted(
            articles[e.path].identifiers.items(), key=lambda tuple_: tuple_[1]
        )
    ))


def filter_errors(
    filter_function: typing.Callable[[error_types.LinkError], typing.Dict[int, typing.List[error_types.LinkError]]],
    errors: typing.Dict[int, typing.List[error_types.LinkError]]
) -> typing.Dict[int, typing.List[error_types.LinkError]]:
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
        changed_cwd = file_utils.ChangeDirectory(args.root)  # Keep alive to maintain directory change  # noqa: F841

    filenames = []
    if args.all:
        filenames = file_utils.list_all_articles_and_newsposts()
    else:
        filenames = list(filter(lambda x: file_utils.is_article(x) or file_utils.is_newspost(x), args.target))

    redirects = redirect_parser.load_redirects("wiki/redirect.yaml")
    exit_code = 0

    articles = {}
    for filename in filenames:
        a = article_parser.parse(filename)
        articles[a.path] = a

    all_errors = []
    error_count = 0
    link_count = 0
    error_file_count = 0
    file_count = 0
    separate = args.separate if args.format != "github" else True

    for _, article in sorted(articles.items()):
        if not args.in_outdated_articles and (article.front_matter.get("outdated", False) or article.front_matter.get("outdated_translation", False)):
            continue

        link_count += sum(len(_.links) for _ in article.lines.values())
        file_count += 1

        errors = link_checker.check_article(article, redirects, articles, args.case_sensitive)

        if not args.to_sections_in_outdated_translations:
            errors = filter_errors(
                lambda e: not ((isinstance(e, error_types.MissingIdentifierError) or
                               isinstance(e, error_types.BrokenRedirectIdentifierError)) and
                               e.translation_outdated), errors)

        if not args.to_sections_in_missing_translations:
            errors = filter_errors(
                lambda e: not ((isinstance(e, error_types.MissingIdentifierError) or
                               isinstance(e, error_types.BrokenRedirectIdentifierError)) and
                               e.no_translation_available), errors)

        if not errors:
            continue

        error_file_count += 1
        error_count += sum(len(e) for e in errors.values())

        if exit_code == 0 and args.format != "json":
            print_error(args.case_sensitive)
        exit_code = 1

        if args.format != "json":
            print_errors(errors, article, args.separate)
            print()

        all_errors.append(error_json(errors, article, separate))

    if exit_code == 0:
        print_clean()
        print()

    if args.format == "json":
        if args.separate:
            print(json.dumps(list(chain(*all_errors))))
        else:
            print(json.dumps(all_errors))

    if args.format == "github":
        print("::group::Annotations")
        for error in islice(chain(*all_errors), 10):
            print("::error file={},line={},col={},title={}::{}".format(
                error["path"],
                error["lineno"],
                error["column"],
                error["type"],
                error["text"]
            ))
        print("::endgroup::")

    if args.format != "json":
        print_count(error_count, link_count, error_file_count, file_count)

    if args.root:
        del changed_cwd
    return exit_code


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
