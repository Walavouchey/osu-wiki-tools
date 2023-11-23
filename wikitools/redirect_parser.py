import typing

Redirects = typing.Dict[str, typing.Tuple[str, int]]


def unquote_and_trim(s):
    s = s.strip()
    if (s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'"):
        return s[1:-1]
    return s


def load_redirects(path: str) -> Redirects:
    """
    Read redirects from a YAML dictionary file (done manually to preserve line numbers).
    """

    redirects = {}
    with open(path, 'r', encoding='utf-8') as fd:
        for line_number, line in enumerate(fd, start=1):
            split = line.split(':')
            try:
                redirects[unquote_and_trim(split[0])] = (unquote_and_trim(split[1]), line_number)
            except IndexError:
                pass
    return redirects
