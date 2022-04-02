import collections

from wikitools import console


class LinkError:
    def pretty(self):
        return f'{console.blue("Note:")} {repr(self)}'


class LinkNotFound(LinkError, collections.namedtuple('LinkNotFound', 'location')):
    """
    An error indicating missing link: a text or binary file does not exist, and there is no such redirect.
    """

    location: str

    def __repr__(self):
        return f'"{self.location}" was not found'


class BrokenRedirect(
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


class MissingReference(LinkError, collections.namedtuple('MissingReference', 'location')):
    """
    An error indicating that a reference-style link is missing its counterpart:
    [link][link_ref] exists, but [link_ref]: /wiki/Path/To/Article does not.
    """

    location: str

    def __repr__(self):
        return f'No corresponding reference found for "{self.location}"'
