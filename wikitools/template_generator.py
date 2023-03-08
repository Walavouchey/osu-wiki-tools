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
    

# Enums have the benefit of being printable
class FilterOperator(StrEnum):
    IS = "is"
    IS_NOT = "is not"
    HAS = "has"
    HAS_NOT = "has not"
    AND = "and"
    OR = "or"


class FilterOperatorFunction():
    IS: typing.Callable[[str, str], bool] = lambda a, b : a == b
    IS_NOT: typing.Callable[[str, str], bool] = lambda a, b : a != b
    HAS: typing.Callable[[str, str], bool] = lambda a, b : b in a
    HAS_NOT: typing.Callable[[str, str], bool] = lambda a, b : b not in a
    AND: typing.Callable[[bool, bool], bool] = lambda a, b : a and b
    OR: typing.Callable[[bool, bool], bool] = lambda a, b : a or b


FILTER_OPERATORS = OrderedDict({
    FilterOperator.IS_NOT.value: FilterOperatorFunction.IS_NOT,
    FilterOperator.IS.value: FilterOperatorFunction.IS,
    FilterOperator.HAS_NOT.value: FilterOperatorFunction.HAS_NOT,
    FilterOperator.HAS.value: FilterOperatorFunction.HAS,
    FilterOperator.AND.value: FilterOperatorFunction.AND,
    FilterOperator.OR.value: FilterOperatorFunction.OR,
})


FILTER_OPERATORS_STR = OrderedDict({
    FilterOperator.IS_NOT.value: FilterOperator.IS_NOT,
    FilterOperator.IS.value: FilterOperator.IS,
    FilterOperator.HAS_NOT.value: FilterOperator.HAS_NOT,
    FilterOperator.HAS.value: FilterOperator.HAS,
    FilterOperator.AND.value: FilterOperator.AND,
    FilterOperator.OR.value: FilterOperator.OR,
})


class Filter():
    """
    Filter, with extremely simple syntax for ease of implementation (for now).
    
    There are no parentheses.

    Operators are evaluated in order:
        A is not B
        A is B
        A has not B
        A has B
        A and B [ and C ...]
        A or B [ or C ...]
    """

    def __init__(self, filter_string: str):
        # "A is B and C has D and E is F"
        # --> ('A', 'is', 'B', 'and', 'C', 'has', 'D', 'and', 'E' is 'F')
        tokens = tuple(s.strip() for s in regex_split("(" + "|".join(f" {op} " for op in FILTER_OPERATORS.keys()) + ")", filter_string))

        match self._build_ast(tokens):
            case tuple(result):
                self.op_tree = result
            case _:
                raise ValueError

    def _build_ast(self, tokens: tuple) -> typing.Union[tuple, str]:
        # ('A', 'is', 'B', 'and', 'C', 'has', 'D', 'and', 'E' is 'F')
        # --> (and,
        #         ('A', 'is', 'B'),
        #         ('C', 'has', 'D', 'and', 'E', 'is', 'F'))
        # ...
        # --> (and,
        #         (is, 'A', 'B'),
        #         (and,
        #             (has, 'C', 'D'),
        #             (is, 'E', 'F')))
        #
        # lisp expression
        for op_name in reversed(FILTER_OPERATORS.keys()):
            for i, token in enumerate(tokens):
                if token == op_name:
                    op = FILTER_OPERATORS_STR[op_name]
                    arguments = (
                        self._build_ast(tokens[:i]),
                        self._build_ast(tokens[i + 1:])
                    )
                    return (op, *arguments)

        if type(tokens[0]) is not str:
            raise ValueError
        return tokens[0]

    def apply(self, row: TableRow) -> bool:
        return self._evaluate(self.op_tree, row)

    def _evaluate(self, tree: tuple, row: TableRow) -> bool:
        op = tree[0]
        args = tree[1:]
        evaluated_args = tuple(
            arg
            if type(arg) is bool else
            Format(arg).apply(row)
            if type(arg) is str else
            self._evaluate(arg, row)
            for arg in args
        )
        return FILTER_OPERATORS[op.value](*evaluated_args)

    op_tree: tuple
