import collections
import typing
from pathlib import Path

from wikitools import console, link_parser, reference_parser


class LinkError:
    _colourise_fragment_only: bool = False
    link: link_parser.Link
    """
    Base class for errors specific to links
    """

    def pretty(self):
        return f'{console.blue("Note:")} ' + repr(self).replace("\n", "\n      ")

    def pretty_location(self, article_path, lineno):
        return "{}: {}".format(
            console.yellow(":".join((article_path, str(lineno), str(self.pos)))),
            self.link.colourise_location(fragment_only=self._colourise_fragment_only)
        )

    @property
    def pretty_link(self):
        return self.link.colourise_link(fragment_only=self._colourise_fragment_only)

    @property
    def pos(self):
        return self.link.start + 1


class MalformedLinkError(
    LinkError,
    collections.namedtuple('MalformedLinkError', 'link reason')
):
    """
    An error indicating an erroneous link (for example, with several leading slashes, or including the wiki article file name).
    """

    link: link_parser.Link
    reason: str

    def __repr__(self):
        return f'"{self.link.raw_location}": {self.reason}'


class LinkNotFoundError(
    LinkError,
    collections.namedtuple('LinkNotFound', 'link reference resolved_location')
):
    """
    An error indicating a missing link: a text or binary file does not exist, and there is no redirect for it.
    """

    link: link_parser.Link
    reference: typing.Optional[reference_parser.Reference]
    resolved_location: str

    def __repr__(self):
        return '"{}" was not found {}'.format(
            self.resolved_location,
            f"(reference at line {self.reference.lineno})"
            if self.reference else ''
        )


class BrokenRedirectError(
    LinkError,
    collections.namedtuple('BrokenRedirect', 'link resolved_location redirect_lineno redirect_destination')
):
    """
    An error indicating broken redirect: the redirect either points to a non-existent article, or another redirect (which is not allowed).
    """

    link: link_parser.Link
    resolved_location: str
    redirect_lineno: int
    redirect_destination: str

    _colourise_fragment_only_in_redirect: bool = False

    def __repr__(self):
        return 'Broken redirect (redirect.yaml:{}: {} --> {})'.format(
            self.redirect_lineno,
            self.resolved_location.lower(),
            link_parser.Link.colourise_location_static(*self.redirect_destination.split("#"), fragment_only=self._colourise_fragment_only_in_redirect)
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
    collections.namedtuple('MissingIdentifier', 'link path identifier no_translation_available translation_outdated')
):
    """
    An error indicating that in another article there is no heading or identifier tag
    that would produce #such-reference.
    """

    _colourise_fragment_only = True

    link: link_parser.Link
    path: str
    identifier: str
    # for news posts, these two should be False
    no_translation_available: bool  # also implies a link to and from a translation
    translation_outdated: bool

    def __repr__(self):
        return 'There is no heading or tag with identifier "{}" in "{}"{}'.format(
            self.identifier, self.path,
            ' (no translation available)' if self.no_translation_available
            else ' (outdated translation)' if self.translation_outdated
            else ''
        )

    @property
    def pos(self):
        return self.link.fragment_start + 1


class BrokenRedirectIdentifierError(
    LinkError,
    # TODO: would be cool to just inherit from these two
    # BrokenRedirectError, MissingIdentifierError,
    collections.namedtuple('BrokenRedirectIdentifier', 'link resolved_location redirect_lineno redirect_destination path identifier no_translation_available translation_outdated')
):
    """
    An error indicating that a redirect points to a non-existent heading or identifier tag
    that would produce such #identifier
    """

    link: link_parser.Link
    resolved_location: str
    redirect_lineno: int
    redirect_destination: str
    path: str
    identifier: str
    # for news posts, these two should be False
    no_translation_available: bool  # also implies a link to and from a translation
    translation_outdated: bool

    _colourise_fragment_only_in_redirect: bool = True

    def __repr__(self):
        return BrokenRedirectError.__repr__(self) + "\n" + MissingIdentifierError.__repr__(self)


class FileError():
    """
    Base class for errors specific to files and folder structure
    """

    def pretty(self):
        return f'{console.blue("Note:")} ' + repr(self).replace("\n", "\n      ")

    def pretty_location(self):
        raise NotImplementedError()


class MissingEnglishVersionError(
    FileError,
    collections.namedtuple('MissingEnglishVersionError', 'file')
):
    """
    An error indicating that the `en.md` file is missing in a wiki folder with other markdown files
    """

    # for now this spits errors per file, with the idea of using github annotations
    # (which can't be folder-specific afaik)
    file: Path

    def __repr__(self):
        return f"{self.file} is missing a corresponding en.md file in the same folder"

    def pretty_location(self):
        return console.yellow(self.file)
