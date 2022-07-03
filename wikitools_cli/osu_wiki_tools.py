#!/usr/bin/env python3

"""
Tools useful for osu! wiki contributors
"""

import argparse
import sys

from wikitools_cli.commands import check_outdated_articles, check_links, check_yaml, what_links_here

from wikitools_cli.VERSION import VERSION

commands = [
    {
        "name": "check-outdated-articles",
        "help": "check if articles are correctly outdated",
        "entry": check_outdated_articles.main,
    },
    {
        "name": "check-links",
        "help": "find broken wikilinks",
        "entry": check_links.main,
    },
    {
        "name": "check-yaml",
        "help": "validate front matter and standalone YAML files",
        "entry": check_yaml.main,
    },
    {
        "name": "what-links-here",
        "help": "find links that link to an article",
        "entry": what_links_here.main,
    },
]


def split_args(args):
    main_args = []
    subcommand_args = []
    found_command_name = False

    for arg in args:
        if found_command_name:
            subcommand_args.append(arg)
        else:
            main_args.append(arg)
        if any(arg == command["name"] for command in commands):
            found_command_name = True

    return main_args, subcommand_args


def parse_args(args):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-V", "--version", action="version", version=VERSION)

    subparsers = parser.add_subparsers(title="commands", metavar="command")
    for command in commands:
        subparser = subparsers.add_parser(command["name"], help=command["help"], add_help=False)
        subparser.set_defaults(func=command["entry"])

    # any parameters after the command name are validated in the command's respective file
    # this main parser would error on them as unrecognised, so they're cut away here
    main_args, subcommand_args = split_args(args)

    parsed_args = parser.parse_args(main_args)
    if len(vars(parsed_args)) == 0:
        # program was invoked without any arguments
        parser.print_help()
        sys.exit(1)

    return parsed_args, subcommand_args


def main(*args):
    parsed_args, subcommand_args = parse_args(args)
    return parsed_args.func(*subcommand_args)


def console_main():
    sys.exit(main(*sys.argv[1:]))


if __name__ == '__main__':
    console_main()
