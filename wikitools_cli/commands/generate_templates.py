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

import yaml

from wikitools.article_parser import FrontMatterDetector
from wikitools import comment_parser, console, file_utils

class TableRow(typing.List[str]):
    header: typing.List[str]

    def __init__(self, row: typing.Optional[typing.List[str]] = None, header: typing.Optional[typing.List[str]] = None):
        if header:
            self.header = header
        if row:
            for cell in row:
                self.append(cell)

    def get(self, key: str):
        # TODO: may raise a ValueError
        return self[self.header.index(key)]


class Table():
    def __init__(
        self,
        csv_file: typing.Optional[str] = None,
        header: typing.Optional[typing.List[str]] = None,
        alignments: typing.Optional[typing.List[str]] = None,
    ):
        self.header: typing.List[str] = []
        self.alignments = TableRow([], self.header)
        self.rows: typing.List[TableRow] = []

        if csv_file:
            with open(csv_file, "r", encoding="utf-8", newline="") as file:
                reader = csv.reader(file, delimiter=",", quotechar="\"")
                self.header = next(reader)
                for row in reader:
                    self.rows.append(TableRow(row, self.header))

        if header:
            self.header = header

        if alignments:
            self.alignments = TableRow(alignments, self.header);


    def __repr__(self):
        return self.__str__()

    def __str__(self):
        s = io.StringIO()
        self.print(file=s)
        output = s.getvalue()
        s.close()
        return output

    def copy(self):
        copy = Table()
        copy.header = self.header
        copy.alignments = self.alignments
        copy.rows = self.rows
        return copy

    @staticmethod
    def __justify(string: str, length: int, alignments: str) -> str:
        if alignments == ":--":
            return string.ljust(length, " ")
        elif alignments == ":-:":
            return string.center(length, " ")
        elif alignments == "--:":
            return string.rjust(length, " ")
        raise NotImplemented

    @staticmethod
    def __expand_alignment(alignment: str, length: int) -> str:
        return alignment[0] + alignment[1] * (length - 2) + alignment[2]

    @staticmethod
    def __apply_filter(row: TableRow, filter_string: str) -> bool:
        return eval(filter_string)

    def filtered(self, filter_string: str, columns: typing.Optional[typing.List[str]] = None):
        """
        Creates a new table using a filter string (evaluated arbitrary Python expression) and column list
        to determine inclusion.
        """

        table = Table()
        alignments = self.alignments if self.alignments else TableRow([":--"] * len(self.header), self.header)

        if columns is not None:
            # TODO: this may raise a ValueError from header.index
            column_indices = [self.header.index(column_name) for column_name in columns]
            table.header = [self.header[i] for i in column_indices]
            table.alignments = TableRow([alignments[i] for i in column_indices], self.header)
            table.rows = [
                TableRow([row[i] for i in column_indices], self.header)
                for row in self.rows
                if self.__apply_filter(row, filter_string)
            ]
            for row in self.rows:
                if self.__apply_filter(row, filter_string):
                    table.rows.append(TableRow([row[i] for i in column_indices], self.header))
        else:
            table.header = self.header
            table.alignments = alignments
            table.rows = list(filter(lambda row : self.__apply_filter(row, filter_string), self.rows))

        return table

    def sorted(self, sort_key: str):
        copy = self.copy()
        copy.rows = sorted(copy.rows, key=eval(sort_key))
        return copy

    def print(self, **kwargs) -> None:
        print("| " + " | ".join(self.header) + " |", **kwargs)
        print("| " + " | ".join(self.alignments if self.alignments else [":--"] * len(self.header)) + " |", **kwargs)
        for row in self.rows:
            print("| " + " | ".join(row) + " |", **kwargs)

    def print_pretty(self, **kwargs) -> None:
        alignments = self.alignments if self.alignments else [":--"] * len(self.header)
        header_and_rows = [copy(self.header)]
        for row in self.rows:
            header_and_rows.append(list(row))

        column_lengths: typing.List[int] = [
            max(
                max(
                len(cell) for cell in
                [row[column_no] for row in header_and_rows] # column cells
                ),
                3 # alignments row can't be compacted further
            )
            for column_no in range(len(self.header))
        ]

        print("| " + " | ".join([
            self.__justify(cell, length, alignment) for cell, length, alignment in zip(self.header, column_lengths, alignments)
        ]) + " |", **kwargs)

        print("| " + " | ".join([
            self.__expand_alignment(alignment, length) for alignment, length in zip(alignments, column_lengths)
        ]) + " |", **kwargs)

        for row in self.rows:
            print("| " + " | ".join([
                self.__justify(cell, length, alignment) for cell, length, alignment in zip(row, column_lengths, alignments)
            ]) + " |", **kwargs)

    header: typing.List[str] = []
    alignments: TableRow = TableRow()
    rows: typing.List[TableRow] = []


class Icons():
    osu: str = "![](/wiki/shared/icon/osu)"
    soundcloud: str = "![](/wiki/shared/icon/soundcloud)"
    youtube: str = "![](/wiki/shared/icon/youtube)"
    spotify: str = "![](/wiki/shared/icon/spotify)"
    bandcamp: str = "![](/wiki/shared/icon/bandcamp)"


def link(text: str, link: str):
    if not text or not link:
        return ""
    return f"[{text}]({link})"


def load_generation_descriptors(path: typing.Union[str, pathlib.Path]) -> typing.List[typing.Tuple[int, str, str, dict]]:
    """
    Extracts generation descriptors, which look like this:

        <!--
        [descriptor_name] [version]
        
        Optional description

        ---
        [yaml_data]
        ---
        -->

    All components need to appear in order.

    Returns a list of tuples of (line, descriptor_name, version, yaml_data).
    """

    if isinstance(path, str):
        path = pathlib.Path(path)

    generation_descriptors: typing.List[typing.Tuple[int, str, str, dict]] = []

    comment_reader = comment_parser.CommentParser()
    front_matter_reader = FrontMatterDetector()
    with path.open('r', encoding='utf-8') as fd:
        allow = False
        name = ""
        version = ""
        buffer = io.StringIO()
        for lineno, line in enumerate(fd, start=1):
            comment_reader.parse(line)
            in_front_matter: bool = front_matter_reader.in_front_matter(line)

            if comment_reader.in_multiline and not allow:
                # look for name and version
                if line.strip():
                    split = line.split(" ")
                    if len(split) == 2:
                        name, version = (s.strip() for s in split)
                        allow = True

            elif comment_reader.in_multiline and allow:
                # look for yaml
                if in_front_matter and line.strip() != "---":
                    buffer.write(line)

            elif not comment_reader.in_multiline and allow:
                data = buffer.getvalue()

                if data:
                    # yaml extracted
                    generation_descriptors.append((lineno, name, version, yaml.safe_load(data)))

                name = ""
                version = ""
                buffer = io.StringIO()
                allow = False

    return generation_descriptors


def save_tables(path: typing.Union[str, pathlib.Path], tables: typing.List[typing.Tuple[int, str]]) -> None:
    if isinstance(path, str):
        path = pathlib.Path(path)


    tmpdir = tempfile.TemporaryDirectory()
    tmpfile = (pathlib.Path(tmpdir.name) / "temp.md")
    with path.open('r', encoding='utf-8') as original:
        with tmpfile.open('w', encoding='utf-8') as new:
            #for lineno, line in enumerate(original):
            lineno = 0
            while True:
                try:
                    line = next(original)
                except StopIteration:
                    break

                if any(lineno == table[0] for table in tables):
                    # we're on a line of interest, but which table was it?
                    table = list(filter(None, ((table[1] if lineno == table[0] else None) for table in tables)))[0]

                    # skip over blank line between comment and potential table below, as enforced by remark
                    line = next(original)
                    lineno += 1

                    # skip a over lines containing existing table
                    did_skip = False
                    while line.startswith("|"):
                        # TODO: if the file ends right after a table, this raises a StopIteration
                        # which is fine because it should never happen
                        line = next(original)
                        lineno += 1
                        did_skip = True

                    # print new table
                    new.write("\n")
                    new.write(table)
                    if not did_skip:
                        new.write("\n")

                if not any(lineno == table[0] for table in tables):
                    # we're not at any special line
                    new.write(line)

                lineno += 1

    shutil.move(tmpfile.as_posix(), path.as_posix())


def eval_on_row(expr: str, row: TableRow):
    return eval(expr)


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
        descriptors = load_generation_descriptors(filename)
        tables = []

        for descriptor in descriptors:
            line, name, version, spec_yaml = descriptor

            data_table = Table(csv_file=spec_yaml["table"]["data"])

            #data_table.filtered(sys.argv[1], sys.argv[2:]).print_pretty()
            display_table = Table(header=spec_yaml["table"]["header"], alignments=spec_yaml["table"]["alignments"])
            for row in data_table.rows:
                if eval_on_row(spec_yaml["table"]["filter"], row):
                    display_table.rows.append(
                        TableRow([
                                eval_on_row(spec_yaml["table"]["format"][i], row).strip()
                                for i in range(len(display_table.header))
                            ],
                            display_table.header
                        )
                    )
            final_table = display_table.sorted(spec_yaml["table"]["sort_key"])
            #final_table.print_pretty()
            tables.append((line, str(final_table)))

        save_tables(filename, tables)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
