import enum
import typing
from urllib import parse

from wikitools import console, reference_parser


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
    #             ^ start                                                  ^ end
    start: int
    end: int

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
    alt_text: str

    @property
    def content(self):
        return self.raw_location if not self.alt_text else f"{self.raw_location} {self.alt_text}"

    @property
    def full_link(self):
        if self.is_reference:
            return f"[{self.title}][{self.content}]"
        else:
            return f"[{self.title}]({self.content})"

    @property
    def fragment_start(self):
        """
        0-based position of a hash sign, if the link has a #fragment. Otherwise, the same value as its end.
        """
        return self.start + len(self.title) + 2 + len(self.parsed_location.path) + 1

    def colorise_link(self, fragment_only=False):
        return "{title_in_braces}{left_brace}{location}{extra}{right_brace}".format(
            title_in_braces=console.green(f"[{self.title}]"),
            left_brace=console.green('[') if self.is_reference else console.green('('),
            location=self.colorise_location(fragment_only=fragment_only),
            extra=" " + console.blue(self.alt_text) if self.alt_text else "",
            right_brace=console.green(']') if self.is_reference else console.green(')'),
        )

    def colorise_location(self, fragment_only=False):
        if fragment_only:
            return "".join((
                console.green(self.parsed_location.path),
                console.red('#' + self.parsed_location.fragment)
            ))
        return console.red(self.raw_location)

    def resolve(
        self, references: reference_parser.References
    ) -> typing.Union['Link', typing.Optional[reference_parser.Reference]]:
        if not self.is_reference:
            return self
        return references.get(self.parsed_location.path)

    # Whether the link is a reference-style link. The only difference is that
    # `location` is a reference and needs to be resolved later.
    #
    # The syntax for such links is the same as regular links:
    #    [text][reference]
    #
    # The reference can then later be defined at the start of a new line:
    #    [reference]: link
    is_reference: bool


def find_link(s: str, index=0) -> typing.Optional[Link]:
    """
    Using the state machine, find the first Markdown link found in the string `s` after the `index` position.
    The following are considered links (alt text or title may be missing):
        - [title](/loca/ti/on "Alt text")
        - ![title](/path/to/image "Alt text), with ! not being considered a part of the link
        - [title][reference], with exact locations found separately via find_reference()
    """

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

                raw_location = s[location: extra]
                return Link(
                    raw_location=raw_location,
                    parsed_location=parse.urlparse(raw_location),
                    title=s[start + 1: location - 2],
                    alt_text=s[extra: end],
                    start=start,
                    end=end,
                    is_reference=False
                )
            continue

        if state == State.REFERENCE:
            if brackets.closed(c):
                # end of a complete reference-style link
                end = i
                raw_location = s[location: end]
                return Link(
                    raw_location=raw_location,
                    parsed_location=parse.urlparse(raw_location),
                    title=s[start + 1: location - 2],
                    alt_text="",
                    start=start,
                    end=end,
                    is_reference=True
                )
            continue

    return None


def find_links(line: str) -> typing.List[Link]:
    """
    Iteratively extract all links from a line.
    """

    results = []
    index = 0
    match = find_link(line, index)
    while match:
        results.append(match)
        match = find_link(line, match.end + 1)
    return results
