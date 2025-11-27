import argparse
import json
import sys
import typing

from wikitools.article_parser import load_front_matter, save_front_matter


class KeyValue(typing.NamedTuple):
    key: str
    value: str


class KeyValueAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        try:
            items = [KeyValue(*(s.strip() for s in v.split(":", 1))) for v in values]
        except TypeError:
            parser.error(f"{option_string or self.dest}: value must be of format key:value")
        setattr(namespace, self.dest, items)


def parse_args(args):
    parser = argparse.ArgumentParser(usage="%(prog)s front-matter [options]")
    parser.add_argument("file", type=argparse.FileType("r", encoding="utf-8"), help="Markdown file to edit")
    parser.add_argument("-p", "--print", nargs="*", help="front matter items to print in JSON (or everything by default)")
    parser.add_argument("-s", "--set", nargs="+", action=KeyValueAction, metavar="KEY:VALUE", help="front matter items to add or edit")
    parser.add_argument("-r", "--remove", nargs="+", metavar="KEY", help="front matter items to remove if they exist")
    return parser.parse_args(args)


def main(*args):
    args = parse_args(args)
    old_front_matter = load_front_matter(args.file)
    front_matter = dict(old_front_matter)

    if args.print is not None:
        to_print = {}
        for item in args.print or front_matter.keys():
            try:
                to_print[item] = front_matter[item]
            except KeyError:
                to_print[item] = None
        print(json.dumps(to_print, indent=4))

    if args.set:
        for item in args.set:
            front_matter[item.key] = item.value

    if args.remove:
        for item in args.remove:
            del front_matter[item]

    if front_matter != old_front_matter:
        save_front_matter(args.file.name, front_matter)

    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
