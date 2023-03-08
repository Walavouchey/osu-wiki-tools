from collections import OrderedDict
from copy import copy
import csv
from enum import Enum, StrEnum
import io
import pathlib
from re import split as regex_split
import typing


import yaml


from wikitools.article_parser import FrontMatterDetector
from wikitools.template_generator import Filter, Alignment, SortOrder
from wikitools import comment_parser, link_parser


class TableTemplateDescriptor():
    def __init__(self, line: int, name: str, version: str, data: dict):
        self.line = line
        self.name = name
        self.version = version
        self._data = data

    def _get(self, path: list) -> typing.Union[dict, list, str, None]:
        result = None
        try:
            result = self._data[path[0]]
            for key in path[1:]:
                result = result[key]
        except KeyError:
            return None
        return result

    line: int
    name: str
    version: str
    _data: dict

    @property
    def data(self) -> typing.Optional[str]:
        match self._get(["table", "data"]):
            case str(result):
                return result
            case _:
                return None

    @property
    def header(self) -> typing.Optional[typing.List[str]]:
        match self._get(["table", "header"]):
            case list(result):
                return result
            case _:
                return None

    @property
    def alignments(self) -> typing.Optional[typing.List[Alignment]]:
        match self._get(["table", "alignments"]):
            case list(alignments):
                temp = [alignment_from_string(s) for s in alignments]
                return [Alignment.LEFT if not a else a for a in temp]
            case _:
                return None

    @property
    def formats(self) -> typing.Optional[typing.List[Format]]:
        match self._get(["table", "format"]):
            case list(formats):
                return [Format(f) for f in formats]
            case _:
                return None

    @property
    def filter(self) -> typing.Optional[Filter]:
        match self._get(["table", "filter"]):
            case str(filter_):
                return Filter(filter_)
            case _:
                return None

    @property
    def sort_by(self) -> typing.Optional[str]:
        match self._get(["table", "sort", "by"]):
            case str(result):
                return result
            case _:
                return None

    @property
    def sort_order(self) -> typing.Optional[SortOrder]:
        match self._get(["table", "sort", "order"]):
            case str(sort_order):
                return sort_order_from_string(sort_order)
            case _:
                return None

    @property
    def split_by(self) -> typing.Optional[str]:
        match self._get(["table", "split", "by"]):
            case str(result):
                return result
            case _:
                return None

    @property
    def split_sort_order(self) -> typing.Optional[SortOrder]:
        match self._get(["table", "split", "order"]):
            case str(sort_order):
                return sort_order_from_string(sort_order)
            case _:
                return None

    @property
    def split_prefix_format(self) -> typing.Optional[Format]:
        match self._get(["table", "split", "prefix_format"]):
            case str(format_):
                return Format(format_)
            case _:
                return None

def load_template_descriptors(path: typing.Union[str, pathlib.Path]) -> typing.List[TableTemplateDescriptor]:
    """
    Extracts template descriptors, which look like this:

        <!--
        [name] [version]

        Optional description

        ---
        [yaml_data]
        ---
        -->

    All components need to appear in order.

    Returns a list of TableTemplateDescriptor, which has the line, name, version,
    and other properties to access the yaml data.
    """

    if isinstance(path, str):
        path = pathlib.Path(path)

    template_descriptors: typing.List[TableTemplateDescriptor] = []

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
                    template_descriptors.append(TableTemplateDescriptor(lineno, name, version, yaml.safe_load(data)))

                name = ""
                version = ""
                buffer = io.StringIO()
                allow = False

    return template_descriptors


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
        alignments: typing.Optional[typing.List[Alignment]] = None,
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
            self.alignments = TableRow(self._stringify_alignments(alignments), self.header);

    @staticmethod
    def _stringify_alignments(alignments: typing.List[Alignment]) -> typing.List[str]:
        return [markdown_string_from_alignment(a) for a in alignments]

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
    def _justify(string: str, length: int, alignments: str) -> str:
        if alignments == ":--":
            return string.ljust(length, " ")
        elif alignments == ":-:":
            return string.center(length, " ")
        elif alignments == "--:":
            return string.rjust(length, " ")
        raise NotImplemented

    @staticmethod
    def _expand_alignment(alignment: str, length: int) -> str:
        return alignment[0] + alignment[1] * (length - 2) + alignment[2]

    def filter(self, filter_: Filter):
        """
        Filters the table using a filter function
        """

        self.alignments = self.alignments if self.alignments else TableRow([":--"] * len(self.header), self.header)
        self.rows = list(filter(lambda row : filter_.apply(row), self.rows))

        return self

    def columns(self, columns: typing.List[str]):
        """
        Selects columns to use in table
        """

        alignments = self.alignments if self.alignments else TableRow([":--"] * len(self.header), self.header)
        column_indices = [self.header.index(column_name) for column_name in columns]
        self.header = [self.header[i] for i in column_indices]
        self.alignments = TableRow([alignments[i] for i in column_indices], self.header)
        self.rows = [
            TableRow([row[i] for i in column_indices], self.header)
            for row in self.rows
        ]

        return self

    def sort(self, key: str, order: SortOrder):
        reverse = order == SortOrder.DESCENDING
        # TODO: may raise ValueError
        self.rows = sorted(self.rows, key=lambda row : row.get(key).lower(), reverse=reverse)
        return self

    def print(self, **kwargs) -> None:
        print("| " + " | ".join(self.header) + " |", **kwargs)
        print("| " + " | ".join(
            self.alignments
            if self.alignments else [":--"] * len(self.header)) + " |",
            **kwargs
        )
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
            self._justify(cell, length, alignment) for cell, length, alignment in zip(self.header, column_lengths, alignments)
        ]) + " |", **kwargs)

        print("| " + " | ".join([
            self._expand_alignment(alignment, length) for alignment, length in zip(alignments, column_lengths)
        ]) + " |", **kwargs)

        for row in self.rows:
            print("| " + " | ".join([
                self._justify(cell, length, alignment) for cell, length, alignment in zip(row, column_lengths, alignments)
            ]) + " |", **kwargs)

    header: typing.List[str] = []
    alignments: TableRow = TableRow()
    rows: typing.List[TableRow] = []
