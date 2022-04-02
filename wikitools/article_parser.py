import os
import typing

from wikitools import link_parser, comment_parser, identifier_parser, errors, redirect_parser, reference_parser


class ArticleLine(typing.NamedTuple):
    raw_line: str
    links: typing.List[link_parser.Link]


class DetailedError(typing.NamedTuple):
    link: link_parser.Link
    error: errors.LinkError


class Article:
    """
    A wiki article, which contains some parts from the text file considered important:
        - Only lines containing links, with the full list of parsed links
        - List of references for reference-style links, usually found at the bottom of the article
        - List of identifiers, which #can-be-referred-to from other articles
    """

    directory: str
    filename: str
    cached_lines: typing.Dict[int, str]
    references: reference_parser.References
    identifiers: list

    def __init__(
        self, path: str,
        lines: typing.Dict[int, ArticleLine],
        references: reference_parser.References,
        identifiers: list,
    ):
        self.directory, self.filename = path.rsplit(os.sep, 1)
        self.lines = lines
        self.references = references
        self.identifiers = identifiers

    @property
    def path(self) -> str:
        return os.path.join(self.directory, self.filename)

    def check_links(self, redirects: redirect_parser.Redirects):
        """
        Try resolving links in the article either to another articles, or files.
        """

        result = {}
        article_directory = os.path.relpath(self.directory, 'wiki/')
        for lineno, line in self.lines.items():
            for link in line.links:
                error = link_parser.check_link(redirects, self.references, article_directory, link)
                if error is not None:
                    result.setdefault(lineno, []).append(DetailedError(link=link, error=error))

        return result


def parse(path: str) -> Article:
    """
    Read an article line by line, extracting links, identifiers and references as we go.
    Objects inside <!-- HTML comments -->, both single and multiline, are skipped.
    """

    path = path.replace('\\', '/')
    if path.startswith("./"):
        path = path[2:]

    saved_lines = {}
    references = {}
    identifiers = []

    in_multiline = False
    with open(path, 'r', encoding='utf-8') as fd:
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

            identifier = identifier_parser.extract_identifier(line)
            if identifier is not None:
                identifiers.append(identifier)

            if line.startswith('['):
                reference = reference_parser.extract(line.strip(), lineno=lineno)
                if reference is not None:
                    references[reference.name] = reference
                    saved_lines[lineno] = ArticleLine(raw_line=line, links=[reference])

    return Article(path, saved_lines, references, identifiers)
