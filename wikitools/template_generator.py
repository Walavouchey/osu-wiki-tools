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
from wikitools import comment_parser, link_parser
from wikitools.table_row import TableRow


FORMAT_TAG_LEFT = "<<"
FORMAT_TAG_RIGHT = ">>"
FORMAT_TAG_ACTION_SEPARATOR = ":"
FORMAT_TAG_LIST_SEPARATOR = "|"


def mode_icon(mode: str) -> str:
    match mode:
        case "osu!":
            return "![](/wiki/shared/icon/osu.png)"
        case "osu!taiko":
            return "![](/wiki/shared/icon/taiko.png)"
        case "osu!catch":
            return "![](/wiki/shared/icon/catch.png)"
        case "osu!mania":
            return "![](/wiki/shared/icon/mania.png)"
        case _:
            return ""


def icon_link(link: str) -> str:
    if "osu.ppy.sh" in link or "assets.ppy.sh" in link:
        return f"[![](/wiki/shared/icon/osu.png)]({link})"
    elif "soundcloud.com" in link:
        return f"[![](/wiki/shared/icon/soundcloud.png)]({link})"
    elif "youtube.com" in link or "youtu.be" in link:
        return f"[![](/wiki/shared/icon/youtube.png)]({link})"
    elif "spotify.com" in link:
        return f"[![](/wiki/shared/icon/spotify.png)]({link})"
    elif "bandcamp.com" in link:
        return f"[![](/wiki/shared/icon/bandcamp.png)]({link})"
    else:
        return ""


class Action(Enum):
    # TODO: add TRANSLATE
    MODE_ICON = mode_icon
    ICON_LINK = icon_link


def action_from_string(action_string) -> typing.Optional[Action]:
    match action_string:
        case "mode icon":
            return Action.MODE_ICON
        case "icon link":
            return Action.ICON_LINK
        case _:
            return None


class Alignment(Enum):
    CENTRE = 0
    LEFT = 1
    RIGHT = 2


def alignment_from_string(alignment_string: str) -> typing.Optional[Alignment]:
    match alignment_string:
        case "left": 
            return Alignment.LEFT
        case "right": 
            return Alignment.RIGHT
        case "centre": 
            return Alignment.CENTRE
        case _:
            return None


def markdown_string_from_alignment(alignment: Alignment) -> str:
    match alignment:
        case Alignment.CENTRE:
            return ":-:"
        case Alignment.LEFT:
            return ":--"
        case Alignment.RIGHT:
            return "--:"


class SortOrder(Enum):
    ASCENDING = 0
    DESCENDING = 1


def sort_order_from_string(sort_order_string: str) -> typing.Optional[SortOrder]:
    match sort_order_string:
        case "ascending": 
            return SortOrder.ASCENDING
        case "descending": 
            return SortOrder.DESCENDING
        case _:
            return None


class Tag():
    def __init__(self, columns: typing.List[str], action: typing.Optional[Action]):
        self.columns = columns
        self.action = action

    columns: typing.List[str]
    action: typing.Optional[Action]


class Format():
    # TODO: condense documentation
    """
    A template format string.

    Any format tag is replaced by the corresponding value of the column for a particular row.
    
        Hello, my name is <<Name>>!

        -> Hello, my name is John Smith!

    If multiple columns are provided, the first non-empty value will be used.
        
        Find more music from <<Artist>> at <<SoundCloud link | Bandcamp link>>!

        -> Find more music from Camellia at <Bandcamp link>

    One of a predetermined set of functions can be specified to be applied to the value

        <<translate: Word>> means <<Word>> in French.

        -> fromage means cheese in French

    Empty space between empty values are automatically removed.

        <<icon link: SoundCloud>> <<icon link: Spotify>> <<icon link: Bandcamp>>

        -> [/wiki/shared/icon/soundcloud.png](<SoundCloud link>) [/wiki/shared/icon/bandcamp.png](<Bandcamp link>)
    """

    def __init__(self, format_string: str):
        if type(format_string) is not str:
            raise ValueError
        self._format = []
        index = 0
        while True:
            next_tag = self._find_tag(format_string, index)
            string: str = ""
            if not next_tag:
                # store remaining string content
                string = format_string[index:]
                if string:
                    self._format.append(string)
                break

            left, right = next_tag

            split = format_string[left + len(FORMAT_TAG_LEFT):right].split(FORMAT_TAG_ACTION_SEPARATOR)
            if len(split) == 0 or len(split) > 2:
                # malformed tag, skip
                index = right + len(FORMAT_TAG_RIGHT)
                continue

            if len(split) == 2:
                action_string, rest = split
                action = action_from_string(action_string.strip())
            else:
                action = None
                rest = split[0]
            
            columns = [s.strip() for s in rest.split(FORMAT_TAG_LIST_SEPARATOR)]

            # store non-tag content up to this tag
            string = format_string[index:left]
            if string:
                self._format.append(string)

            # complete tag
            self._format.append(Tag(columns=columns, action=action))

            index = right + len(FORMAT_TAG_RIGHT)

    def _find_tag(self, string: str, start: int) -> typing.Optional[typing.Tuple[int, int]]:
        """
        Returns the location of the next potential tag if any in a tuple of (left, right)

            <<action: Column name>>
            ^ left               ^ right

        """
        left = string.find(FORMAT_TAG_LEFT, start)
        if left == -1:
            return None
        right = string.find(FORMAT_TAG_RIGHT, left + len(FORMAT_TAG_LEFT))
        if right == -1:
            return None

        return (left, right)


    @staticmethod
    def _prune_spaces(evaluated: typing.List[str]) -> typing.List[str]:
        """
        Prune spaces in between tags that evaluate to nothing
        to make sure things like "<<Tag 1>> <<Tag 2>> <<Tag 3>>" don't leave random spaces
        if a tag returns nothing.
        This is algorithmically a little wack but it works as intended.
        """

        pruned = copy(evaluated)
        for i, evaluated_component in enumerate(evaluated):
            if evaluated_component.isspace():
                empty_before: bool = not evaluated[i - 1] if i != 0 else False
                empty_after: bool = not evaluated[i + 1] if i != len(evaluated) - 1 else False
                if empty_before or empty_after:
                    pruned[i] = ""
            elif evaluated_component == "":
                space_before: bool = evaluated[i - 1].isspace() if i != 0 else False
                space_after: bool = evaluated[i + 1].isspace() if i != len(evaluated) - 1 else False
                if space_before and space_after:
                    pruned[i] = " "

        return pruned

    @staticmethod
    def _prune_links(evaluated: str) -> str:
        """
        Prune markdown links that do not have a link part
        to make sure things like "[<<Track>>](<<Link>>)" don't leave empty links
        if a tag returns nothing
        """

        links = link_parser.find_links(evaluated)
        pruned = copy(evaluated)

        offset = 0
        if links:
            for link in links:
                if not link.alt_text:
                    pruned = pruned[:link.start + offset] + pruned[link.end + 1 + offset:]
                    offset -= link.end - link.start + 1
                elif not link.raw_location:
                    pruned = pruned[:link.start] + link.alt_text + pruned[link.end + 1:]
                    offset -= link.end - link.start + 1 - len(link.raw_location)

        return pruned

    def apply(self, row: TableRow) -> str:
        evaluated: typing.List[str] = []
        
        for component in self._format:
            match component:
                case str():
                    evaluated += component
                case Tag(columns=columns, action=action):
                    try:
                        value: str = next(filter(None, (row.get(c) for c in columns)))
                    except StopIteration:
                        evaluated.append("")
                        continue
                    except KeyError:
                        evaluated.append("")
                        continue
                    
                    if action:
                        value = action(value)

                    evaluated.append(value)

        pruned = "".join(self._prune_spaces(evaluated))
        pruned = self._prune_links(pruned)

        return pruned

    _format: typing.List[typing.Union[str, Tag]]


class FilterMode(StrEnum):
    AND = "and"
    OR = "or"

class FilterModeFunction(Enum):
    AND: typing.Callable[[bool, bool], bool] = lambda a, b : a and b
    OR: typing.Callable[[bool, bool], bool] = lambda a, b : a or b

FILTER_MODES = {
    FilterMode.AND.value: FilterModeFunction.AND,
    FilterMode.OR.value: FilterModeFunction.OR,
}

FILTER_MODES_STR = {
    FilterMode.AND.value: FilterMode.AND,
    FilterMode.OR.value: FilterMode.OR,
}


class FilterOperator(StrEnum):
    IS = "is"
    HAS = "has"

class FilterOperatorFunction(Enum):
    IS: typing.Callable[[str, str], bool] = lambda a, b : a == b
    HAS: typing.Callable[[str, str], bool] = lambda a, b : b in a

FILTER_OPERATORS = OrderedDict({
    FilterOperator.IS.value: FilterOperatorFunction.IS,
    FilterOperator.HAS.value: FilterOperatorFunction.HAS,
})


class Filter():
    """
    Filter, with extremely simple syntax for ease of implementation (for now).

    Example:

        filter:
          include:
            - A is B
            - C is D
          exclude:
            - F has G
            - H is i
          include_mode: and # default: and
          exclude_mode: or # default: or
    """

    def __init__(self, filter_descriptor: dict):
        self.include_mode = self._get_filter_mode(filter_descriptor, "include_mode", self.default_include_mode)
        self.exclude_mode = self._get_filter_mode(filter_descriptor, "exclude_mode", self.default_exclude_mode)

        self.includes = self._get_filter(filter_descriptor, "include")
        self.excludes = self._get_filter(filter_descriptor, "exclude")

    def _get_filter_mode(self, filter_descriptor: dict, key: str, default: FilterMode) -> FilterMode:
        try:
            match filter_descriptor[key]:
                case str(filter_mode):
                    return FILTER_MODES_STR.get(filter_mode, default)
                case _:
                    return default
        except KeyError:
            return default

    def _get_filter(self, filter_descriptor: dict, key: str) -> typing.List[typing.Tuple[FilterOperatorFunction, Format, str]]:
        try:
            match filter_descriptor[key]:
                case str(predicate):
                    return [self._parse_predicate(predicate)]
                case list(predicates):
                    return [self._parse_predicate(p) for p in predicates]
                case _:
                    return []
        except KeyError:
            return []

    def apply(self, row: TableRow) -> bool:
        # include = predicate_A FilterModeFunction predicate_B ...
        include = self._reduce_bools(list(
            filter_op_func(format_.apply(row), value)
            for filter_op_func, format_, value in self.includes
        ), FILTER_MODES[self.include_mode.value], True)

        exclude = self._reduce_bools(list(
            filter_op_func(format_.apply(row), value)
            for filter_op_func, format_, value in self.excludes
        ), FILTER_MODES[self.exclude_mode.value], False)

        return include and not exclude

    # TODO: stop assuming valid input
    @staticmethod
    def _parse_predicate(predicate: str) -> typing.Tuple[FilterOperatorFunction, Format, str]:
        # predicate: "<<Format>> FilterOperator value"
        a, filter_mode, b = (s.strip() for s in predicate.split(" ")[:3])
        return (FILTER_OPERATORS[filter_mode], Format(a), b)

    def _reduce_bools(self, bools: typing.List[bool], filter_mode_function: FilterModeFunction, default: bool) -> bool:
        if len(bools) == 0:
            return default
        if len(bools) == 1:
            return bools[0]
        return self._reduce_bools([filter_mode_function(bools[0], bools[1]), *bools[2:]], filter_mode_function, default)


    default_include_mode: FilterMode = FilterMode.AND
    default_exclude_mode: FilterMode = FilterMode.OR

    include_mode: FilterMode
    exclude_mode: FilterMode
    includes: typing.List[typing.Tuple[FilterOperatorFunction, Format, str]]
    excludes: typing.List[typing.Tuple[FilterOperatorFunction, Format, str]]
