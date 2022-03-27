import argparse
import os
import sys
import typing

from wikitools import comment_parser, console, link_parser, redirect_parser


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
        highlighted_line += s[prev_index:link.link_start]
        highlighted_line += link.full_coloured_link
        prev_index = link.link_end + 1
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
    error_count = 0
    match_count = 0
    error_file_count = 0
    file_count = 0
    for filename in filenames:
        filename = filename.replace('\\', '/')
        if filename.startswith("./"):
            filename = filename[2:]
        if any((
            not filename.endswith(".md"),
            "TEMPLATE" in filename,
            "README" in filename,
            "Article_styling_criteria" in filename,
        )):
            continue

        file_count += 1
        with open(filename, 'r', encoding='utf-8') as fd:
            references = link_parser.find_references(fd)

            in_multiline = False
            for linenumber, line in enumerate(fd, start=1):
                comments = comment_parser.find_comments(line, in_multiline)
                if comments:
                    in_multiline = comments[-1].end == -1

                matches = link_parser.find_links(line)
                bad_links = []
                all_notes = []
                for match in matches:
                    if comment_parser.is_in_comment(match.link_start, comments):
                        continue
                    match_count += 1

                    if match.content == "/wiki/Sitemap":
                        continue

                    success, notes = link_parser.check_link(redirects, references, directory(filename), match)
                    if success:
                        continue
                    error_count += 1
                    bad_links.append(match)
                    all_notes += notes

                    if exit_code == 0:
                        print_error()
                    exit_code = 1

                    print(f"{console.yellow(filename)}:{linenumber}:{match.link_start + 1}: {console.red(match.location)}")

                if all_notes:
                    print('\n'.join(all_notes))


                if bad_links:
                    print()
                    error_file_count += 1
                    if args.separate:
                        for link in bad_links:
                            print(highlight_links(line, [link]), end="\n\n")
                    else:
                        print(highlight_links(line, bad_links), end="\n\n")

    if exit_code == 0:
        print_clean()
        print()

    print_count(error_count, match_count, error_file_count, file_count)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
