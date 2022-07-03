#!/usr/bin/env python3

import argparse
import pathlib
import os
import sys
import typing

from wikitools import article_parser, console, link_parser, redirect_parser, file_utils


def s(i: int, s: str) -> str:
    return f"{i} {s}{'s' if i != 1 else ''}"


def print_count(links: int, matches: int, link_files: int, files: int):
    print(f"{console.blue('Note:')} Found {s(links, 'link')} in {s(link_files, 'file')} ({s(matches, 'link')} in {s(files, 'file')} checked).")


def highlight_links(s: str, links: typing.List[link_parser.Link]) -> str:
    highlighted_line = ""
    prev_index = 0
    for link in links:
        highlighted_line += s[prev_index: link.start]
        highlighted_line += link.colourise_link()
        prev_index = link.end + 1
    highlighted_line += s[prev_index: -1]
    return highlighted_line

def pretty_location(path, lineno, pos, location):
    return f"{console.yellow(path)}:{lineno}:{pos}: {console.red(location)}"


def parse_args(args):
    parser = argparse.ArgumentParser(usage="%(prog)s what-links-here [options] target")
    parser.add_argument("target", help="path to the article you want to check, relative to the repository root")
    parser.add_argument("-s", "--separate", action='store_true', help="print links that appear on the same line separately")
    parser.add_argument("-r", "--root", help="specify repository root, current working directory assumed otherwise")
    return parser.parse_args(args)


def main(*args):
    args = parse_args(args)

    if args.root:
        changed_cwd = file_utils.ChangeDirectory(args.root)

    search_target = pathlib.Path(args.target)
    if not search_target.exists():
        print(f'{console.red("Error:")} entered target file "{args.target}" does not exist.\n')
        del changed_cwd
        sys.exit(1)

    filenames = file_utils.list_all_articles_and_newsposts()

    redirects = redirect_parser.load_redirects("wiki/redirect.yaml")

    articles: typing.Dict[str, article_parser.Article] = {}
    for filename in filenames:
        a = article_parser.parse(filename)
        articles[a.path] = a

    match_count = 0
    link_count = 0
    match_file_count = 0
    file_count = 0

    for _, a in sorted(articles.items()):
        link_count += sum(len(_.links) for _ in a.lines.values())
        file_count += 1

        matches: typing.Dict[int, typing.List[link_parser.Link]] = {}
        for lineno, line in a.lines.items():
            local_links = []
            for link in line.links:
                reference = link.resolve(a.references)
                if reference is None and link.is_reference:
                    continue
                
                location = reference.parsed_location.path if reference else link.parsed_location.path
                parsed_location = reference.parsed_location if reference else link.parsed_location

                if parsed_location.scheme or parsed_location.netloc:
                    continue

                if ((parsed_location.scheme == "http" or parsed_location.scheme == "https") and
                    parsed_location.netloc == "osu.ppy.sh" and location.startswith("/home/news/")):
                    target = pathlib.Path(location[1:] + ".md").relative_to("home")
                    location = '/' + target.as_posix()

                    if not target.exists():
                        continue

                if not location.startswith("/wiki/"):
                    current_article_dir = os.path.relpath(a.directory, 'wiki')
                    location = f"/wiki/{current_article_dir}/{location}"
                
                target = pathlib.Path(location[1:])
                # no article? could be a redirect
                if not target.exists():
                    redirect_source = target.relative_to('wiki').as_posix()
                    try:
                        redirect_destination, _ = redirects[redirect_source.lower()]
                    except KeyError:
                        continue

                    target = pathlib.Path('wiki') / redirect_destination
                    if not target.exists():
                        continue

                if target == search_target:
                    local_links.append(link)
            if local_links:
                matches[lineno] = local_links
        if not matches:
            continue

        match_file_count += 1

        for lineno, matches_on_line in sorted(matches.items()):
            match_count += len(matches_on_line)
            for l in matches_on_line:
                print(pretty_location(a.path, lineno, l.start + 1, l.raw_location))

            print()
            if args.separate:
                for e in matches_on_line:
                    print(highlight_links(a.lines[lineno].raw_line, [e]), end="\n\n")
            else:
                print(highlight_links(a.lines[lineno].raw_line, matches_on_line), end="\n\n")

    print_count(match_count, link_count, match_file_count, file_count)
    if args.root:
        del changed_cwd
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
