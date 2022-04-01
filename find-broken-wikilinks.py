import argparse
import itertools
import os
import sys
import typing

from wikitools import article_parser, comment_parser, console, link_parser, redirect_parser


def directory(filename: str) -> str:
    return filename[filename.find('/') + 1:filename.rfind('/')]


def print_error():
    print(f"{console.red('Error:')} Some wiki or image links in the files you've changed have errors.\n")
    print("This can happen in one of the following ways:\n")
    print("- The article or image that the link points to has since been moved or renamed (make sure to match capitalisation)")
    print("- The link simply contains typos or formatting errors")
    print("- The link works, but contains locale selection (e.g. /wiki/en/Article_styling_criteria instead of /wiki/Article_styling_criteria)")
    print("- The link works, but contains URL-escaped characters (https://en.wikipedia.org/wiki/Percent-encoding). This only applies for links to articles and images inside the wiki.")
    print("- The link works, but incurs multiple redirects. Use a direct link instead.")
    print("\nFor more information on link style, see https://osu.ppy.sh/wiki/en/Article_styling_criteria/Formatting#links.\n")


def print_clean():
    print("Notice: No broken wiki or image links detected.")


def s(i: int, s: str) -> str:
    return f"{i} {s}{'s' if i != 1 else ''}"


def print_count(errors: int, matches: int, error_files: int, files: int):
    print(f"{console.blue('Note:')} Found {s(errors, 'error')} in {s(error_files, 'file')} ({s(matches, 'link')} in {s(files, 'file')} checked).")


def highlight_links(s: str, links: typing.List[link_parser.Link]) -> str:
    highlighted_line = ""
    prev_index = 0
    for link in links:
        highlighted_line += s[prev_index:link.start]
        highlighted_line += link.full_coloured_link
        prev_index = link.end + 1
    highlighted_line += s[prev_index:-1]
    return highlighted_line


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--target", nargs='*', help="paths to the articles you want to check")
    parser.add_argument("-a", "--all", action='store_true', help="check all articles")
    parser.add_argument("-s", "--separate", action='store_true', help="print errors that appear on the same line separately")
    return parser.parse_args(args)


def file_iterator(roots: list):
    for item in roots:
        if os.path.isdir(item):
            for root, _, filenames in os.walk(item):
                for f in filenames:
                    filepath = os.path.join(root, f)
                    yield filepath
        elif os.path.isfile(item):
            yield item


def main():
    args = parse_args(sys.argv[1:])
    if not args.target and not args.all:
        print("Notice: No articles to check.")
        sys.exit(0)

    filenames = []
    if args.all:
        filenames = file_iterator(["wiki", "news"])
    else:
        filenames = args.target

    redirects = redirect_parser.load_redirects("wiki/redirect.yaml")
    exit_code = 0

    articles = {}
    for filename in filenames:
        if any((
            not filename.endswith(".md"),
            "TEMPLATE" in filename,
            "README" in filename,
            "Article_styling_criteria" in filename,
        )):
            continue

        a = article_parser.Article.parse_file(filename)
        articles.setdefault(a.directory, []).append(a)

    error_count = 0
    link_count = 0
    error_file_count = 0
    file_count = 0

    for a in itertools.chain.from_iterable(articles.values()):
        link_count += sum(len(_.links) for _ in a.lines.values())
        file_count += 1

        errors, bad_links = a.check_links(redirects)
        if not errors:
            continue

        error_count += len(errors)
        error_file_count += 1
        if exit_code == 0:
            print_error()
        exit_code = 1

        for error, location in errors:
            print(location.pretty())
            print(error.pretty())

        for lineno, links in sorted(bad_links.items()):
            if args.separate:
                for link in links:
                    print(highlight_links(a.lines[lineno].raw_line, [link]), end="\n\n")
            else:
                print(highlight_links(a.lines[lineno].raw_line, links), end="\n\n")

    if exit_code == 0:
        print_clean()
        print()

    print_count(error_count, link_count, error_file_count, file_count)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
