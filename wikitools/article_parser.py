import collections
import pathlib
import typing

from wikitools import link_parser, comment_parser, identifier_parser, reference_parser


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
    lines: typing.Dict[int, str]
    references: reference_parser.References
    identifiers: set

    def __init__(
        self, path: pathlib.Path,
        lines: typing.Dict[int, ArticleLine],
        references: reference_parser.References,
        identifiers: set,
    ):
        self.filename = path.name
        self.directory = str(path.parent.as_posix())
        self.lines = lines
        self.references = references
        self.identifiers = identifiers

    @property
    def path(self) -> str:
        return '/'.join((self.directory, self.filename))


def parse(path: typing.Union[str, pathlib.Path]) -> Article:
    """
    Read an article line by line, extracting links, identifiers and references as we go.
    Anything inside <!-- HTML comments -->, both single and multiline, is skipped.
    """

    if isinstance(path, str):
        path = pathlib.Path(path)

    saved_lines = {}
    references = {}
    cnt = collections.Counter()
    identifiers = set()

    in_multiline = False
    with path.open('r', encoding='utf-8') as fd:
        for lineno, line in enumerate(fd, start=1):
            comments = comment_parser.parse(line, in_multiline)
            if comments:
                in_multiline = comments[-1].end == -1

            # everything in a multiline comment doesn't count
            if in_multiline:
                continue

            links_on_line = list(filter(
                lambda l: not(
                    l.content == '/wiki/Sitemap' or
                    comment_parser.is_in_comment(l.start, comments)
                ),
                link_parser.find_links(line)
            ))
            # cache meaningful lines. in our case, lines with links and references
            if links_on_line:
                saved_lines[lineno] = ArticleLine(raw_line=line, links=links_on_line)

            identifier = identifier_parser.extract_identifier(line, links_on_line)
            if identifier is not None:
                cnt[identifier] += 1
                if identifier in identifiers:
                    identifier = '{}.{}'.format(identifier, cnt[identifier] - 1)
                identifiers.add(identifier)

            if line.startswith('['):
                reference = reference_parser.extract(line.strip(), lineno=lineno)
                if reference is not None:
                    references[reference.name] = reference
                    saved_lines[lineno] = ArticleLine(raw_line=line, links=[reference])

    return Article(path, saved_lines, references, identifiers)
