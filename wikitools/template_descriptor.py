import io
import pathlib
import typing


import yaml


from wikitools.article_parser import FrontMatterDetector
from wikitools.template_generator import Filter, Format, Alignment, SortOrder
from wikitools.template_generator import alignment_from_string, sort_order_from_string
from wikitools import comment_parser


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
            case dict(filter_):
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
