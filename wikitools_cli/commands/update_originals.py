#!/usr/bin/env python3

"""
This script updates the "wiki/osu! originals" article using data from the following spreadsheet:

https://docs.google.com/spreadsheets/d/1o--KQKvNF9JtmZmTGuzN6KyBpFwoQDr98TWRHhrzh-E/edit#gid=879770106
"""

import argparse
import sys
import typing
import os
from csv import DictReader
from copy import copy
import io
from collections import Counter

from wikitools import console, errors as error_types, file_utils

try:
    from googleapiclient.discovery import build # type: ignore
    from googleapiclient.errors import HttpError # type: ignore
    GOOGLE_CLIENT_IMPORTED = True
except ImportError as error:
    GOOGLE_CLIENT_IMPORTED = False
    GOOGLE_CLIENT_IMPORT_ERROR = error


API_KEY_ENV = "GOOGLE_SHEETS_API_KEY"
try:
    API_KEY = os.environ[API_KEY_ENV]
except KeyError:
    API_KEY = ""

TOTAL_ROWS = 0
TRACKS_SEEN: Counter = Counter()


def list_table_to_dict_table(table: typing.List[typing.List[str]]) -> typing.List[typing.Dict[str, str]]:
    header = table[0]
    new_table = []
    for row in table[1:]:
        new_table.append({ header: value for header, value in zip(header, row) })
    return new_table


def get_spreadsheet_range(spreadsheet_id, range_name):
    """
    Retrieves a range of cell values from a Google Sheet.

    Raises HttpError when either authentication or retrieval fails.
    """

    service = build("sheets", "v4", developerKey=API_KEY)

    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=range_name)
        .execute()
    )

    rows = result.get("values", [])
    column_count = len(rows[0])

    rows = [row + [""] * (column_count - len(row)) for row in rows]
    return list_table_to_dict_table(rows)


class Table():
    def __init__(
        self,
        rows: typing.List[typing.Dict[str, str]],
        header: typing.List[str],
        alignments: typing.List[str],
    ):
        self.rows = rows
        self.header = header
        self.alignments = alignments

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
    def _justify(string: str, length: int, alignment: str) -> str:
        if alignment == ":--":
            return string.ljust(length, " ")
        elif alignment == ":-:":
            return string.center(length, " ")
        elif alignment == "--:":
            return string.rjust(length, " ")
        raise NotImplemented

    @staticmethod
    def _expand_alignment(alignment: str, length: int) -> str:
        return alignment[0] + alignment[1] * (length - 2) + alignment[2]

    @staticmethod
    def _dict_row_to_list(row: typing.Dict[str, str], header: typing.List[str]) -> typing.List[str]:
        return [row[column] for column in header]

    def print(self, **kwargs) -> None:
        print("| " + " | ".join(self.header) + " |", **kwargs)
        print("| " + " | ".join(
            self.alignments
            if self.alignments else [":--"] * len(self.header)) + " |",
            **kwargs
        )
        for row in self.rows:
            print("| " + " | ".join(self._dict_row_to_list(row, self.header)) + " |", **kwargs)

    def print_pretty(self, **kwargs) -> None:
        alignments = self.alignments if self.alignments else [":--"] * len(self.header)
        header_and_rows = [copy(self.header)]
        for row in self.rows:
            header_and_rows.append(self._dict_row_to_list(row, self.header))

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
                self._justify(cell, length, alignment) for cell, length, alignment in zip(self._dict_row_to_list(row, self.header), column_lengths, alignments)
            ]) + " |", **kwargs)

    rows: typing.List[typing.Dict[str, str]]
    header: typing.List[str]
    alignments: typing.List[str]


class MarkdownSection():
    """
    Represents a markdown section and its tree of subsections

    Example usage:
        tree = MarkdownSection(markdown_string)
        tree[0][0][0] = new_text
        tree[0][0][1][0].nodes[1] = new_text
        new_markdown = str(tree)
    """
    def __init__(self, markdown_string: str, heading_level: int=0):
        self.nodes = []
        self.subsections = []

        section_nodes = []
        nodes = markdown_string.split("\n\n")
        subheading_level = heading_level + 1
        subsection_found = False

        # find subsections
        for i, node in enumerate(nodes):
            if node.startswith("#" * subheading_level + " ") and not subsection_found:
                # new section
                subsection_found = True

            elif subsection_found and (node.startswith("#" * subheading_level + " ") or i == len(nodes) - 1):
                # end of section
                if i == len(nodes) - 1:
                    section_nodes.append(node)
                self.subsections.append(MarkdownSection("\n\n".join(section_nodes), subheading_level))
                section_nodes = []

            if subsection_found:
                section_nodes.append(node)
            else:
                self.nodes.append(node)

    def __getitem__(self, key):
        if type(key) is not int:
            raise TypeError(f"Incorrect type: expected int, got {type(key)}")

        return self.subsections[key]

    def __setitem__(self, key, value):
        if type(key) is not int:
            raise TypeError(f"Incorrect type: expected int, got {type(key)}")

        if type(value) is MarkdownSection:
            self.subsections[key] = value

        elif type(value) is str:
            self.subsections[key] = MarkdownSection(value)

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        s = "\n\n".join(self.nodes)
        if self.nodes and self.subsections:
            s += "\n\n"
        if self.subsections:
            s += "\n\n".join(str(section) for section in self.subsections)
        return s

    # Anything before subsections, including content before the heading (i.e. front matter), the heading itself, and paragraphs after the heading
    nodes: typing.List[str]

    # Subsections, if any, with heading levels one greater than that of this section
    subsections: typing.List['MarkdownSection']


def mode_icon(mode: str) -> str:
    split = mode.split(", ")
    if len(split) > 1:
        return " ".join(mode_icon(m) for m in split)
    match mode:
        case "osu":
            return "![](/wiki/shared/mode/osu.png)"
        case "taiko":
            return "![](/wiki/shared/mode/taiko.png)"
        case "catch":
            return "![](/wiki/shared/mode/catch.png)"
        case "mania":
            return "![](/wiki/shared/mode/mania.png)"
        case _:
            return ""


def first(l: typing.List[str]) -> str:
    trimmed = [l for l in l if l]
    if not trimmed:
        return ""
    return trimmed[0]


def maybe_link(text: str, link: str, empty_when_no_link: bool=False) -> str:
    if not link:
        return "" if empty_when_no_link else text
    return f"[{text}]({link})"


def footnote(fa_status: str) -> str:
    match fa_status:
        case "FA_CATALOGUE":
            return "[^fa-catalogue]"
        case "FA":
            return "[^fa]"
        case "FA_FEATURE":
            return "[^fa-feature]"
        case "NONE":
            return ""
        case _:
            return ""


def create_table_ost(data):
    global TOTAL_ROWS
    TOTAL_ROWS += len(data)
    for row in data:
        TRACKS_SEEN[row['Track']] += 1
    return Table(
        [
            {
                "Song": f"[{row['Track']}]({first([row['SoundCloud'], row['Beatmap']])}){footnote(row['FA status'])}",
                "Notes": row['Note']
            } for row in data
        ],
        ["Song", "Notes"],
        [":-:", ":--"]
    )


def create_table_fa_release(data):
    global TOTAL_ROWS
    TOTAL_ROWS += len(data)
    for row in data:
        TRACKS_SEEN[row['Track']] += 1
    return Table(
        [
            {
                "Song": f"[{row['Track']}]({first([row['SoundCloud'], row['YouTube'], row['Spotify'], row['Bandcamp'], row['FA listing']])})"
            } for row in data
        ],
        ["Song"],
        [":-:"]
    )


def create_table_tournament(data):
    global TOTAL_ROWS
    TOTAL_ROWS += len(data)
    for row in data:
        TRACKS_SEEN[row['Track']] += 1
    return Table(
        [
            {
                "Song": f"{maybe_link(row['Track'], first([row['SoundCloud'], row['YouTube'], row['Spotify'], row['Bandcamp'], row['FA listing']]))}{footnote(row['FA status'])}",
                "Beatmap": ", ".join([maybe_link(f"#{i}", beatmap, True) for i, beatmap in enumerate(row['Beatmap'].split(", "), start=1)]),
                "Notes": first([row['Mappool slot'], row['Note']])
            } for row in data
        ],
        ["Song", "Beatmap", "Notes"],
        [":-:", ":-:", ":--"]
    )


def create_table_contest_official(data):
    global TOTAL_ROWS
    TOTAL_ROWS += len(data)
    for row in data:
        TRACKS_SEEN[row['Track']] += 1
    return Table(
        [
            {
                "Song": f"{maybe_link(row['Track'], first([row['SoundCloud'], row['YouTube'], row['Spotify'], row['Bandcamp'], row['FA listing'], row['Asset']]))}{footnote(row['FA status'])}",
                "Beatmap": ", ".join([maybe_link(f"#{i}", beatmap, True) for i, beatmap in enumerate(row['Beatmap'].split(", "), start=1)]),
            } for row in data
        ],
        ["Song", "Beatmap"],
        [":-:", ":-:"]
    )


def create_table_contest_community(data):
    global TOTAL_ROWS
    TOTAL_ROWS += len(data)
    for row in data:
        TRACKS_SEEN[row['Track']] += 1
    return Table(
        [
            {
                "Song": f"{maybe_link(row['Track'], first([row['SoundCloud'], row['YouTube'], row['Spotify'], row['Bandcamp'], row['FA listing']]))}{footnote(row['FA status'])}",
            } for row in data
        ],
        ["Song"],
        [":-:"]
    )


def create_table_standalone_beatmap(data):
    global TOTAL_ROWS
    TOTAL_ROWS += len(data)
    for row in data:
        TRACKS_SEEN[row['Track']] += 1
    return Table(
        [
            {
                "Song": f"{maybe_link(row['Track'], first([row['SoundCloud'], row['YouTube'], row['Spotify'], row['Bandcamp'], row['FA listing']]))}{footnote(row['FA status'])}",
                "Beatmap": ", ".join([maybe_link(f"#{i}", beatmap, True) for i, beatmap in enumerate(row['Beatmap'].split(", "), start=1)]),
            } for row in data
        ],
        ["Song", "Beatmap"],
        [":-:", ":-:"]
    )


def sanitise(string):
    return (
        string
        .replace("\\", "\\\\")
        .replace("_", "\\_")
        .replace("~", "\\~")
        .replace("|", "\\|")
        .replace("<", "\\<")
        .replace(">", "\\>")
    )


def populate_section(csv, event_type, track_type, create_table_func):
    section = ""
    for mode in ["osu", "taiko", "catch", "mania", ""]:
        data = [row for row in csv if row['Type'] == track_type and row['Mode'].split(", ")[0] == mode]
        for event in sorted(list(set(row[event_type] for row in data))):
            data = [row for row in csv if row[event_type] == event]
            section += f"#### {mode_icon(data[0]['Mode'])} {maybe_link(event, data[0][f'{event_type} link'])}"
            section += "\n\n"
            section += str(create_table_func(data)) + "\n"
    return section


def parse_args(args):
    parser = argparse.ArgumentParser(usage="%(prog)s update-originals [options]")
    parser.add_argument("-f", "--csv-file", type=argparse.FileType("r", encoding="utf-8"), help="use a local csv file instead of online retrieval")
    return parser.parse_args(args)


def main(*args):
    args = parse_args(args)

    if args.csv_file:
        reader = DictReader(args.csv_file)
        csv_unsanitised = list(reader)
        print(f"{len(csv_unsanitised)} rows retrieved from local file")
    else:
        if not API_KEY:
            print(f"{console.red('Error:')} Spreadsheet retrieval requires an api key set to the {API_KEY_ENV} environment variable.\n")
            print("See https://support.google.com/googleapi/answer/6158862?hl=en")
            print("and https://console.cloud.google.com/apis/api/sheets.googleapis.com/overview\n")
        if not GOOGLE_CLIENT_IMPORTED:
            print(f"{console.red('Error:')} {GOOGLE_CLIENT_IMPORT_ERROR}. Spreadsheet retrieval requires an optional dependency:\n")
            print("pip install google-api-python-client\n")
        if not API_KEY or not GOOGLE_CLIENT_IMPORTED:
            print("Alternatively, use the --csv-file option (see --help).")
            return 1
        try:
            csv_unsanitised = get_spreadsheet_range("1o--KQKvNF9JtmZmTGuzN6KyBpFwoQDr98TWRHhrzh-E", "raw!A:U")
            print(f"{len(csv_unsanitised)} rows retrieved from online spreadsheet")
        except HttpError as error:
            print(f"{console.red('Error:')} Spreadsheet retrieval failed: {error.status_code}. Make sure the {API_KEY_ENV} environment variable is correct.")
            return 1
        except Exception as error:
            print(f"{console.red('Error:')} Spreadsheet retrieval failed: {error}")
            return 1

    csv = []
    for row in csv_unsanitised:
        row['Track'] = sanitise(row['Track'])
        csv.append(row)
    csv = sorted(csv, key=lambda row: row['Track'].lower())

    table_ost = str(create_table_ost([row for row in csv if row['Type'] == "OST"]))

    table_fa_cysmix = str(create_table_fa_release([row for row in csv if row['Type'] == "FA_RELEASE" and "`cYsmix`:2" in row['Artists']]))
    table_fa_happy30 = str(create_table_fa_release([row for row in csv if row['Type'] == "FA_RELEASE" and "`happy30`:317" in row['Artists']]))
    table_fa_james_landino = str(create_table_fa_release([row for row in csv if row['Type'] == "FA_RELEASE" and "`James Landino`:39" in row['Artists']]))
    table_fa_kiraku = str(create_table_fa_release([row for row in csv if row['Type'] == "FA_RELEASE" and "`kiraku`:101" in row['Artists']]))
    table_fa_kitazawa_kyouhei = str(create_table_fa_release([row for row in csv if row['Type'] == "FA_RELEASE" and "`Kitazawa Kyouhei`:165" in row['Artists']]))
    table_fa_rabbit_house = str(create_table_fa_release([row for row in csv if row['Type'] == "FA_RELEASE" and "`Rabbit House`:242" in row['Artists']]))
    table_fa_yuki = str(create_table_fa_release([row for row in csv if row['Type'] == "FA_RELEASE" and "`yuki.`:4" in row['Artists']]))
    table_fa_zxnx = str(create_table_fa_release([row for row in csv if row['Type'] == "FA_RELEASE" and "`ZxNX`:288" in row['Artists']]))

    section_tournament_official = populate_section(csv, "Tournament", "TOURNAMENT_OFFICIAL", create_table_tournament)
    section_tournament_community = populate_section(csv, "Tournament", "TOURNAMENT_COMMUNITY", create_table_tournament)
    section_contest_official = ""
    section_contest_community = populate_section(csv, "Contest", "CONTEST_COMMUNITY", create_table_contest_community)

    data_contest_official = [row for row in csv if row['Type'] == "CONTEST_OFFICIAL"]
    for contest in sorted(list(set(row['Contest'] for row in data_contest_official))):
        data = [row for row in csv if row['Contest'] == contest]
        section_contest_official += f"#### {maybe_link(contest, data[0]['Contest link'])}"
        section_contest_official += "\n\n"
        section_contest_official += str(create_table_contest_official(data)) + "\n"

    table_standalone = str(create_table_standalone_beatmap([row for row in csv if row['Type'] == "BEATMAP"]))

    with open('wiki/osu!_originals/en.md', "r", encoding="utf-8", newline="\n") as file:
        contents = file.read()

    tree = MarkdownSection(contents)

    tree[0][0][0].nodes[1] = table_ost.strip()

    tree[0][0][1][0].nodes[2] = table_fa_cysmix.strip()
    tree[0][0][1][1].nodes[2] = table_fa_happy30.strip()
    tree[0][0][1][2].nodes[3] = table_fa_james_landino.strip()
    tree[0][0][1][3].nodes[2] = table_fa_kiraku.strip()
    tree[0][0][1][4].nodes[2] = table_fa_kitazawa_kyouhei.strip()
    tree[0][0][1][5].nodes[2] = table_fa_rabbit_house.strip()
    tree[0][0][1][6].nodes[2] = table_fa_yuki.strip()
    tree[0][0][1][7].nodes[2] = table_fa_zxnx.strip()

    tree[0][0][2] = tree[0][0][2].nodes[0] + "\n\n" + section_tournament_official.strip()
    tree[0][0][3] = tree[0][0][3].nodes[0] + "\n\n" + section_tournament_community.strip()
    tree[0][0][4] = tree[0][0][4].nodes[0] + "\n\n" + section_contest_official.strip()
    tree[0][0][5] = tree[0][0][5].nodes[0] + "\n\n" + section_contest_community.strip()

    tree[0][0][6].nodes[2] = table_standalone.strip()

    with open('wiki/osu!_originals/en.md', "w", encoding="utf-8", newline="\n") as file:
        file.write(str(tree))

    unique_tracks  = set(row['Track'] for row in csv)
    duplicates = [(track, count) for track, count in TRACKS_SEEN.items() if count > 1]
    missing = unique_tracks - set(TRACKS_SEEN.keys())
    if len(unique_tracks) != TOTAL_ROWS or TOTAL_ROWS != len(csv) or duplicates or missing:
        print(f"{console.red('Error:')} Data mismatch detected. This could be due to either an issue with the spreadsheet/csv or a bug in the program.")
        print(f"Total tracks read: {len(csv)}")
        print(f"Unique tracks read: {len(unique_tracks)}")
        print(f"Tracks written: {TOTAL_ROWS}")
        print(f"Duplicates written ({len(duplicates)}):" + ("".join([f"\n- {track} ({count} times)" for track, count in duplicates]) or " none"))
        print(f"Missing ({len(missing)}):" + ("".join([f"\n- {track}" for track in list(missing)]) or " none"))

    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
