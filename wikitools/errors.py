import collections

from wikitools import console, link_parser


class LinkError:
    _colorize_fragment_only = False

    def pretty(self):
        return f'{console.blue("Note:")} {repr(self)}'

    def pretty_location(self, article_path, lineno):
        return "{}: {}".format(
            console.yellow(":".join((article_path, str(lineno), str(self.pos)))),
            self.link.colorize_location(fragment_only=self._colorize_fragment_only)
        )

    @property
    def pretty_link(self):
        return self.link.colorize_link(fragment_only=self._colorize_fragment_only)

    @property
    def pos(self):
        return self.link.start + 1


class MalformedLinkError(
    LinkError,
    collections.namedtuple('MalformedLinkError', 'link')
):
    """
    An error indicating an erroneous link (for example, with several leading slashes).
    """

    link: link_parser.Link

    def __repr__(self):
        return f'Incorrect link structure (typo?): "{self.link.raw_location}"'


class LinkNotFoundError(
    LinkError,
    collections.namedtuple('LinkNotFound', 'link resolved_location')
):
    """
    An error indicating missing link: a text or binary file does not exist, and there is no such redirect.
    """

    link: link_parser.Link
    resolved_location: str

    def __repr__(self):
        return f'"{self.resolved_location}" was not found'


class BrokenRedirectError(
    LinkError,
    collections.namedtuple('BrokenRedirect', 'link resolved_location redirect_lineno redirect_destination')
):
    """
    An error indicating broken redirect: an article from the redirect.yaml file does not exist.
    """

    link: link_parser.Link
    resolved_location: str
    redirect_lineno: int
    redirect_destination: str

    def __repr__(self):
        return 'Broken redirect (redirect.yaml:{}: {} --> {})'.format(
            self.redirect_lineno, self.resolved_location.lower(), self.redirect_destination
        )


class MissingReferenceError(
    LinkError,
    collections.namedtuple('MissingReference', 'link')
):
    """
    An error indicating that a reference-style link is missing its counterpart:
    [link][link_ref] exists, but [link_ref]: /wiki/Path/To/Article does not.
    """

    link: link_parser.Link

    def __repr__(self):
        return f'No corresponding reference found for "{self.link.raw_location}"'


class MissingIdentifierError(
    LinkError,
    collections.namedtuple('MissingIdentifier', 'link path identifier translation_available')
):
    """
    An error indicating that in another article there is no heading or any other object
    that would produce #such-reference.
    """

    _colorize_fragment_only = True

    link: link_parser.Link
    path: str
    identifier: str
    translation_available: bool

    def __repr__(self):
        return 'There is no heading or other object with identifier "{}" in "{}"{}'.format(
            self.identifier, self.path, '' if self.translation_available else ' (no translation available)'
        )

    @property
    def pos(self):
        return self.link.fragment_start + 1
