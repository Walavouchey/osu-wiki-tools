import collections
import io
import pathlib
import re
import shutil
import typing

import yaml

from wikitools import code_block_parser, link_parser, comment_parser, identifier_parser, reference_parser

FRONT_MATTER_DELIMITER = '---'
TITLE_INDICATOR = '# '
REQUIRES_QUOTES = re.compile(r".*((: )|(#))")


class Dumper(yaml.Dumper):
    # workaround to make yaml.Dumper write lists with leading indentation
    # (taken from https://github.com/yaml/pyyaml/issues/234#issuecomment-765894586)
    def increase_indent(self, flow=False, *args, **kwargs):
        return super().increase_indent(flow=flow, indentless=False)

    # very complicated way to tell pyYAML to use double quotes and not single quotes
    # (taken from https://github.com/yaml/pyyaml/blob/main/lib/yaml/representer.py)
    def represent_mapping(self, tag, mapping, flow_style=None):
        value = []
        node = yaml.MappingNode(tag, value, flow_style=flow_style)
        if self.alias_key is not None:
            self.represented_objects[self.alias_key] = node
        best_style = True
        if hasattr(mapping, 'items'):
            mapping = list(mapping.items())
            if self.sort_keys:
                try:
                    mapping = sorted(mapping)
                except TypeError:
                    pass
        for item_key, item_value in mapping:
            node_key = self.represent_data(item_key)
            node_value = self.represent_data(item_value)

            # double quotes instead of single quotes (when required)
            if isinstance(item_value, str) and REQUIRES_QUOTES.match(item_value) is not None:
                node_value.style = '"'

            if not (isinstance(node_key, yaml.ScalarNode) and not node_key.style):
                best_style = False
            if not (isinstance(node_value, yaml.ScalarNode) and not node_value.style):
                best_style = False
            value.append((node_key, node_value))
        if flow_style is None:
            if self.default_flow_style is not None:
                node.flow_style = self.default_flow_style
            else:
                node.flow_style = best_style
        return node


class ArticleLine(typing.NamedTuple):
    raw_line: str
    links: typing.List[link_parser.Link]


class Article:
    """
    A wiki article, which contains some parts from the text file considered important:
        - Only lines containing links, with the full list of parsed links
        - List of references for reference-style links, usually found at the bottom of the article
        - List of identifiers, which #can-be-referred-to from other articles
    """

    directory: str
    filename: str
    lines: typing.Dict[int, ArticleLine]
    references: reference_parser.References
    identifiers: typing.Dict[str, int]
    front_matter: dict

    def __init__(
        self, path: pathlib.Path,
        lines: typing.Dict[int, ArticleLine],
        references: reference_parser.References,
        identifiers: typing.Dict[str, int],
        front_matter: dict
    ):
        self.filename = path.name
        self.directory = str(path.parent.as_posix())
        self.lines = lines
        self.references = references
        self.identifiers = identifiers
        self.front_matter = front_matter

    @property
    def path(self) -> str:
        return '/'.join((self.directory, self.filename))


def load_front_matter(fileobj: typing.TextIO) -> dict:
    delimiters = 0
    buffer = io.StringIO()

    offset = fileobj.tell()
    for line in fileobj:
        if line.split('#')[0].strip() == FRONT_MATTER_DELIMITER:
            delimiters += 1
        # Stop on second delimiter, or when it's clear there won't be front matter at all
        if delimiters == 2 or line.startswith(TITLE_INDICATOR):
            break
        buffer.write(line)
    fileobj.seek(offset)

    if delimiters == 2:
        return yaml.safe_load(buffer.getvalue())
    return dict()


class FrontMatterDetector():
    """
    Helper class for keeping track of whether a line is part of front matter.
    Includes delimiter lines.
    """

    def __init__(self):
        self.in_front_matter_ = 0

    in_front_matter_ = False

    def in_front_matter(self, line: str):
        if line.split('#')[0].strip() == FRONT_MATTER_DELIMITER:
            self.in_front_matter_ = not self.in_front_matter_
            return True
        return self.in_front_matter_


def save_front_matter(filepath: str, fm: dict):
    new_path = filepath + '.new'
    with open(new_path, 'w', encoding='utf-8') as new_file:
        if fm:
            new_file.write(FRONT_MATTER_DELIMITER + '\n')
            new_file.write(yaml.dump(
                fm, Dumper=Dumper, default_flow_style=False, indent=2, sort_keys=False, allow_unicode=True,
            ))
            new_file.write(FRONT_MATTER_DELIMITER + '\n\n')

        with open(filepath, "r", encoding='utf-8') as old_file:
            front_matter_detector = FrontMatterDetector()
            for line in old_file:
                # There shouldn't be anything before any front matter, so it's just assumed here
                # There may be cases where the title is preceded by a comment or HTML tags, however
                # Such content is preserved
                if not front_matter_detector.in_front_matter(line) and line.strip():
                    new_file.write(line)
                    new_file.write(old_file.read())
                    break

    shutil.move(new_path, filepath)


def parse(path: typing.Union[str, pathlib.Path]) -> Article:
    """
    Read an article line by line, extracting links, identifiers and references as we go.
    Anything inside <!-- HTML comments -->, both single and multiline, is skipped.
    """

    if isinstance(path, str):
        path = pathlib.Path(path)

    saved_lines = {}
    references = {}
    cnt: typing.Counter[str] = collections.Counter()
    identifiers: typing.Dict[str, int] = {}

    comment_reader = comment_parser.CommentParser()
    code_block_reader = code_block_parser.CodeBlockParser()
    with path.open('r', encoding='utf-8') as fd:
        front_matter = load_front_matter(fd)
        for lineno, line in enumerate(fd, start=1):
            comments = comment_reader.parse(line)
            code_blocks = code_block_reader.parse(line)

            # everything in a multiline comment or code block doesn't count
            if comment_reader.in_multiline or code_block_reader.in_multiline:
                continue

            links_on_line = list(filter(
                lambda link: not (
                    link.content == '/wiki/Sitemap' or
                    comment_parser.is_in_comment(link.start, comments) or
                    code_block_parser.is_in_code_block(link.start, code_blocks)
                ),
                link_parser.find_links(line)
            ))
            # cache meaningful lines. in our case, lines with links and references
            if links_on_line:
                saved_lines[lineno] = ArticleLine(raw_line=line, links=links_on_line)

            identifier, pos = identifier_parser.extract_identifier(line, links_on_line)
            # if a comment contains identifiers, this assumes such a comment at least
            # doesn't appear before an actual identifier. this is a rare occurrence anyway
            if identifier is not None and not comment_parser.is_in_comment(pos, comments):
                cnt[identifier] += 1
                # duplicate identifiers get a suffix
                if identifier in identifiers:
                    identifier = '{}.{}'.format(identifier, cnt[identifier] - 1)
                identifiers[identifier] = lineno

            if line.startswith('['):
                reference = reference_parser.extract(line.strip(), lineno=lineno)
                if reference is not None:
                    references[reference.name] = reference

    return Article(path, saved_lines, references, identifiers, front_matter)
