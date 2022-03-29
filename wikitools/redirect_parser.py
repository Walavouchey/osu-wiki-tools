import os
import typing

from wikitools import console

Redirects = typing.Dict[str, typing.Tuple[str, int]]


def load_redirects(path: str) -> Redirects:
    """
    Read redirects from a string representing YAML dictionary manually to preserve line numbers.
    """

    redirects = {}
    with open(path, 'r', encoding='utf-8') as fd:
        for line_number, line in enumerate(fd, start=1):
            split = line.split('"')
            try:
                redirects[split[1]] = (split[3], line_number)
            except IndexError:
                pass
    return redirects


def check_redirect(redirects: Redirects, link: str):
    link_lower = link.lower()
    try:
        destination, line_no = redirects[link_lower]
    except KeyError:
        note = f"{console.blue('Note:')} \"{link}\" was not found"
        return (False, note)
    if not os.path.exists(f"wiki/{destination}"):
        note = f"{console.blue('Note:')} Broken redirect (redirect.yaml:{line_no}: {link_lower} --> {destination})"
        return (False, note)
    return (True, "")

