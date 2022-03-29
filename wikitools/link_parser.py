import enum
import os
import typing
from urllib import parse

from wikitools import console, redirect_parser

References = typing.Dict[str, typing.Tuple[str, int]]


class Brackets():
    # Helper class keeping track of when brackets open and close
    def __init__(self, left: str, right: str):
        self.left = left
        self.right = right
        self.depth = 0

    left: str
    right: str
    depth: int

    def closed(self, c: str):
        if c == self.left:
            self.depth += 1
        elif c == self.right:
            self.depth -= 1
        if self.depth == 0:
            return True
        return False


class State(enum.Enum):
    IDLE = 0
    START = 1
    INLINE = 2
    REFERENCE = 3


class Link(typing.NamedTuple):
    """
    A Markdown link, inline- or reference-style, external or internal.
    May be relative. Example:

        See [Difficulty Names](/wiki/Beatmap/Difficulty#naming-conventions)

    - title: 'Difficulty Names'
    - raw_location: '/wiki/Beatmap/Difficulty#naming-conventions'
    - parsed_location: urllib.parse.ParseResult with all of its fields

    Another example:

        ![Player is AFK](img/chat-console-afk.png "Player is away from keyboard")

    - title: 'Player is AFK'
    - raw_location: 'img/chat-console-afk.png'
    - parsed_location: urllib.parse.ParseResult with all of its fields
    - alt_text: 'Player is away from keyboard'
    """

    # Link position within the line. Example:
    #   See also: [Difficulty names](/wiki/Beatmap/Difficulty#naming-conventions)
    #             ^ link_start                                                  ^ link_end
    link_start: int
    link_end: int

    # Sections of a link. Example:
    #    ![Player is AFK](img/chat-console-afk.png "Player is away from keyboard")
    #      ^ - title - ^
    #                     ^ ----- location ----- ^
    #                                               ^ ------- alt_text ------- ^
    #                     ^ --------------------- content --------------------- ^
    #     ^ ------------------ full_link / full_coloured_link ------------------ ^
    title: str
    raw_location: str
    parsed_location: parse.ParseResult
    extra: str

    @property
    def content(self):
        return self.raw_location if not self.extra else f"{self.raw_location} {self.extra}"

    @property
    def full_link(self):
        if self.is_reference:
            return f"[{self.title}][{self.content}]"
        else:
            return f"[{self.title}]({self.content})"

    @property
    def full_coloured_link(self):
        return "{title_in_braces}{left_brace}{location}{extra}{right_brace}".format(
            title_in_braces=console.green(f"[{self.title}]"),
            left_brace= console.green('[') if self.is_reference else console.green('('),
            location=console.red(self.raw_location),
            extra=console.blue(self.extra),
            right_brace=console.green(']') if self.is_reference else console.green(')'),
        )

    # Whether the link is a reference-style link. The only difference is that
    # `location` is a reference and needs to be resolved later.
    #
    # The syntax for such links is the same as regular links:
    #    [text][reference]
    #
    # The reference can then later be defined at the start of a new line:
    #    [reference]: link
    is_reference: bool


def child(path: str) -> str:
    return path[path.find('/', 1) + 1:]


def check_link(redirects: redirect_parser.Redirects, references: References, directory: str, link: Link) -> typing.Tuple[bool, typing.List[str]]:
    notes = []

    # dereference the location, if possible
    location = link.parsed_location.path
    parsed_location = link.parsed_location
    if link.is_reference and location in references:
        ref, lineno = references[location]
        location = ref.split(' ')[0].split('#')[0].split('?')[0]
        parsed_location = parse.urlparse(location)
        notes.append(f"{console.blue('Note:')} Reference at line {lineno}: [{location}]: {ref}")
    elif link.is_reference:
        notes.append(f"{console.blue('Note:')} No corresponding reference found for \"{link.raw_location}\"")

    # some external link; don't care
    if parsed_location.scheme:
        return (True, notes)

    # internal link (domain is empty)
    if parsed_location.netloc == '':
        # convert a relative wikilink to absolute
        if not location.startswith("/wiki/"):
            location = f"/wiki/{directory}/{location}"

        # article file exists -> quick win
        # TODO(TicClick): check if a section exists
        if os.path.exists(location[1:]):
            return (True, notes)

        # may have a redirect
        value, redir_note = redirect_parser.check_redirect(redirects, child(location))
        notes.append(redir_note)
        return (value, notes)


def find_link(s: str, index=0) -> typing.Optional[Link]:
    state = State.IDLE

    start = None
    location = None
    extra = None
    end = None

    parens = Brackets('(', ')')
    brackets = Brackets('[', ']')

    for i, c in enumerate(s[index:], start=index):
        if state == State.IDLE and c == '[':
            # potential start of a link
            brackets.depth += 1
            state = State.START
            start = i
            continue

        if state == State.START:
            if brackets.closed(c):
                # the end of a bracket. the link may continue
                # to be inline- or reference-style
                if len(s) <= i + 1:
                    state = state.IDLE
                    continue

                if s[i + 1] == '(':
                    state = State.INLINE
                    location = i + 2
                elif s[i + 1] == '[':
                    state = State.REFERENCE
                    location = i + 2
                else:
                    state = state.IDLE
            continue

        if state == State.INLINE:
            if c == ' ':
                if extra is None:
                    # start of extra part
                    extra = i

            if parens.closed(c):
                # end of a complete link
                end = i
                if extra is None:
                    extra = end

                return Link(
                    raw_location=s[location: extra],
                    parsed_location=parse.urlparse(s[location: extra]),
                    title=s[start + 1: location - 2],
                    extra=s[extra: end],
                    link_start=start,
                    link_end=end,
                    is_reference=False
                )
            continue

        if state == State.REFERENCE:
            if brackets.closed(c):
                # end of a complete reference-style link
                end = i
                return Link(
                    raw_location=s[location: end],
                    parsed_location=parse.urlparse(s[location: end]),
                    title=s[start + 1: location - 2],
                    extra="",
                    link_start=start,
                    link_end=end,
                    is_reference=True
                )
            continue

    return None


def find_links(s: str) -> typing.List[Link]:
    results = []
    index = 0
    match = find_link(s, index)
    while match:
        results.append(match)
        match = find_link(s, match.link_end + 1)
    return results


def find_reference(s: str) -> typing.Optional[typing.Tuple[str, str]]:
    split = s.find(':')
    if split != -1 and s.startswith('[') and s[split - 1] == ']' and s[split + 1] == ' ':
        return (s[1:split - 1], s[split + 2:-1])
    return


def find_references(file) -> References:
    seek = file.tell()
    references = {}
    for linenumber, line in enumerate(file, start=1):
        reference = find_reference(line)
        if reference:
            references[reference[0]] = (reference[1], linenumber)
    file.seek(seek)
    return references
