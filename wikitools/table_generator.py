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
from wikitools.template_generator import markdown_string_from_alignment
from wikitools import comment_parser, link_parser
from wikitools.table_row import TableRow


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
