import collections

from wikitools import console


class LinkError:
    def pretty(self):
        return f'{console.blue("Note:")} {repr(self)}'


class LinkNotFoundError(LinkError, collections.namedtuple('LinkNotFound', 'location')):
    """
    An error indicating missing link: a text or binary file does not exist, and there is no such redirect.
    """

    location: str

    def __repr__(self):
        return f'"{self.location}" was not found'


class BrokenRedirectError(
    LinkError,
    collections.namedtuple('BrokenRedirect', 'location redirect_lineno redirect_destination')
):
    """
    An error indicating broken redirect: an article from the redirect.yaml file does not exist.
    """

    location: str
    redirect_lineno: int
    redirect_destination: str

    def __repr__(self):
        return 'Broken redirect (redirect.yaml:{}: {} --> {})'.format(
            self.redirect_lineno, self.location.lower(), self.redirect_destination
        )


class MissingReferenceError(LinkError, collections.namedtuple('MissingReference', 'location')):
    """
    An error indicating that a reference-style link is missing its counterpart:
    [link][link_ref] exists, but [link_ref]: /wiki/Path/To/Article does not.
    """

    location: str

    def __repr__(self):
        return f'No corresponding reference found for "{self.location}"'


class MissingIdentifierError(
    LinkError,
    collections.namedtuple('MissingIdentifier', 'path identifier translation_available')
):
    """
    An error indicating that in another article there is no heading or any other object
    that would produce #such-reference.
    """

    path: str
    identifier: str
    translation_available: bool

    def __repr__(self):
        return 'There is no heading or other object with identifier "{}" in "{}"{}'.format(
            self.identifier, self.path, '' if self.translation_available else ' (no translation available)'
        )
