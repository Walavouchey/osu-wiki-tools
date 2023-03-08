import argparse
from copy import copy
import csv
import io
import pathlib
import shutil
import sys
import tempfile
import textwrap
import typing

from wikitools import console, file_utils
from wikitools.table_generator import Table
from wikitools.template_generator import Format, SortOrder
from wikitools.table_row import TableRow
from wikitools.template_descriptor import TableTemplateDescriptor, load_template_descriptors


class HeadingTracker():
    """
    Helper class for tracking what section a line is in
    """

    def __init__(self):
        self.heading_path = []

    heading_path: typing.List[str]

    @property
    def current_heading(self) -> typing.Optional[str]:
        return self.heading_path[-1] if self.heading_path else None

    @property
    def current_heading_level(self) -> int:
        return len(self.heading_path)

    def update(self, line: str) -> None:
        if line.startswith("#"):
            current_heading, heading_level = self._parse_heading(line)
            if heading_level > len(self.heading_path):
                self.heading_path.append(current_heading)
            elif heading_level == len(self.heading_path):
                self.heading_path[-1] = current_heading
            else:
                self.heading_path = self.heading_path[0:heading_level - 1]
                self.heading_path.append(current_heading)

    @staticmethod
    def _parse_heading(line):
        current_heading = line.split("#")[-1].strip()
        heading_level = 0
        for c in line:
            if c == "#":
                heading_level += 1
            else:
                break
        return (current_heading, heading_level)


def skip_while(fileobj: typing.TextIO, heading_tracker: HeadingTracker, predicate_to_reach: typing.Callable[[str, HeadingTracker], bool]) -> typing.Tuple[str, int]:
    skipped = 0
    line = ""
    while True:
        try:
            line = next(fileobj)
            skipped += 1
            heading_tracker.update(line)
        except StopIteration:
            if not predicate_to_reach(line, heading_tracker):
                line = ""
            break
        if predicate_to_reach(line, heading_tracker):
            break
    return (line, skipped)


# TODO: maybe refactor this mess
def save_tables(path: typing.Union[str, pathlib.Path], tables: typing.List[typing.Tuple[int, str, bool]]) -> None:
    if isinstance(path, str):
        path = pathlib.Path(path)

    tmpdir = tempfile.TemporaryDirectory()
    tmpfile = (pathlib.Path(tmpdir.name) / "temp.md")
    with path.open('r', encoding='utf-8') as original:
        with tmpfile.open('w', encoding='utf-8') as new:
            #for lineno, line in enumerate(original):
            lineno = 0
            heading_tracker = HeadingTracker()
            while True:
                try:
                    line = next(original)
                    lineno += 1
                    heading_tracker.update(line)
                except StopIteration:
                    break

                if any(lineno == table[0] for table in tables):
                    # we're on a line of interest, but which table was it?
                    table_lineno, table, consume_section = next(filter(None, ((table if lineno == table[0] else None) for table in tables)))

                    # last line of the comment
                    new.write(line)
                    if not line.endswith("\n"):
                        new.write("\n")

                    if consume_section:
                        target_heading_level = heading_tracker.current_heading_level
                        line, skipped_lines = skip_while(
                            original,
                            heading_tracker,
                            # assuming a "split table" should take up the entire section,
                            # consuming any subheadings
                            lambda l, t : l.startswith("#") and t.current_heading_level <= target_heading_level
                        )
                        lineno += skipped_lines
                        heading_tracker.update(line)
                    else:
                        # skip to next piece of content
                        line, skipped_lines = skip_while(original, heading_tracker, lambda l, _ : not l.isspace())
                        lineno += skipped_lines
                        heading_tracker.update(line)

                        # skip over lines containing existing table
                        if line.startswith("|"):
                            line, skipped_lines = skip_while(original, heading_tracker, lambda l, _ : not l.startswith("|"))
                            lineno += skipped_lines
                            heading_tracker.update(line)

                            if line.isspace():
                                line, skipped_lines = skip_while(original, heading_tracker, lambda l, _ : not l.isspace())
                                lineno += skipped_lines
                                heading_tracker.update(line)

                    # print new table
                    new.write("\n")
                    new.write(table.strip())
                    if line:
                        new.write("\n\n")
                        new.write(line)

                elif not any(lineno == table[0] for table in tables):
                    # we're not at any special line
                    new.write(line)

            new.write("\n")

    shutil.move(tmpfile.as_posix(), path.as_posix())


# TODO: maybe refactor this mess
def make_table(descriptor: TableTemplateDescriptor) -> str:
    data_table = Table(csv_file=descriptor.data)

    if descriptor.sort_by:
        data_table.sort(descriptor.sort_by, descriptor.sort_order)

    if descriptor.filter:
        data_table.filter(descriptor.filter)

    display_table = Table(header=descriptor.header, alignments=descriptor.alignments)

    if descriptor.split_by:
        keys = []
        prefixes: typing.List[str] = []
        split_table = []
        split_keys = set()

        for row in data_table.rows:
            split_key = row.get(descriptor.split_by)
            if split_key:
                if split_key not in split_keys:
                    split_table.append(Table(header=descriptor.header, alignments=descriptor.alignments))
                    split_keys.add(split_key)
                    if descriptor.split_prefix_format:
                        prefixes.append(descriptor.split_prefix_format.apply(row))
                    else:
                        prefixes.append("")
                    keys.append(split_key)

                split_table[-1].rows.append(
                    TableRow([
                            descriptor.formats[i].apply(row).strip()
                            for i in range(len(display_table.header))
                        ],
                        display_table.header
                    )
                )

        split_display_table = []
        zipped = list(zip(keys, prefixes, split_table))

        if descriptor.split_sort_order:
            zipped = sorted(zipped, key=lambda x : x[0].lower(), reverse=descriptor.split_sort_order == SortOrder.DESCENDING)

        for _, prefix, table in zipped:
            split_display_table.append(prefix)
            split_display_table.append(str(table).strip())

        split_display_table = list(filter(None, split_display_table))

        return "\n\n".join(split_display_table)
    else:
        for row in data_table.rows:
            display_table.rows.append(
                TableRow([
                        descriptor.formats[i].apply(row).strip()
                        for i in range(len(display_table.header))
                    ],
                    display_table.header
                )
            )

        return str(display_table)


def parse_args(args):
    parser = argparse.ArgumentParser(usage="%(prog)s generate-tables [options]")
    parser.add_argument("-t", "--target", nargs='*', help="paths to the articles you want to generate templates for, relative to the repository root")
    parser.add_argument("-a", "--all", action='store_true', help="generate templates in all articles")
    parser.add_argument("-r", "--root", help="specify repository root, current working directory assumed otherwise")
    return parser.parse_args(args)


def main(*args):
    # begin boilerplate
    args = parse_args(args)
    if not args.target and not args.all:
        print(f"{console.grey('Notice:')} No articles to check.")
        sys.exit(0)

    if args.root:
        changed_cwd = file_utils.ChangeDirectory(args.root)

    filenames = []
    if args.all:
        filenames = file_utils.list_all_articles_and_newsposts()
    else:
        filenames = list(filter(lambda x: file_utils.is_article(x) or file_utils.is_newspost(x), args.target))
    # end boilerplate

    for filename in filenames:
        descriptors = load_template_descriptors(filename)
        tables = []

        for descriptor in descriptors:
            table = make_table(descriptor)
            tables.append((descriptor.line, table, bool(descriptor.split_by)))

        save_tables(filename, tables)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
