import collections


class LinkError:
    pass


class LinkNotFound(LinkError, collections.namedtuple('LinkNotFound', 'location')):
    location: str

    def __repr__(self):
        return f'"{self.location}" was not found'


class BrokenRedirect(
    LinkError,
    collections.namedtuple('BrokenRedirect', 'location redirect_lineno redirect_destination')
):
    location: str
    redirect_lineno: int
    redirect_destination: str

    def __repr__(self):
        return 'Broken redirect (redirect.yaml:{}: {} --> {})'.format(
            self.redirect_lineno, self.location.lower(), self.redirect_destination
        )


class LinkNotFound(LinkError, collections.namedtuple('MissingReference', 'location')):
    location: str

    def __repr__(self):
        return f'No corresponding reference found for "{self.location}"'
