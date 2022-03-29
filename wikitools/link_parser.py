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
    def full_coloured_link(self):
        return "{title_in_braces}{left_brace}{location}{extra}{right_brace}".format(
            title_in_braces=console.green(f"[{self.title}]"),
            left_brace= console.green('[') if self.is_reference else console.green('('),
            location=console.red(self.raw_location),
            extra=" " + console.blue(self.alt_text) if self.alt_text else "",
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


def extract_tail(path: str) -> str:
    """
    Given a path in a file system, return its tail (everything past the first non-root slash). Examples:
        - /wiki/Beatmap/Category -> Beatmap/Category
        - img/users/2.png -> users/2.png
    """
    return path[path.find('/', 1) + 1:]


def check_link(redirects: redirect_parser.Redirects, references: References, directory: str, link: Link) -> typing.Tuple[bool, typing.List[str]]:
    """
    Verify that the link is valid:
        - External links are always assumed valid, since we can't just issue HTTP requests left and right
        - For Markdown references, there exists a dereferencing line with [reference_name]: /lo/ca/ti/on
        - Direct internal links, as well as redirects, must point to existing article files
        - Relative links are parsed under the assumption that
            their parent (current article, where the link is defined) is `directory`
    """

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
        value, redir_note = redirect_parser.check_redirect(redirects, extract_tail(location))
        notes.append(redir_note)
        return (value, notes)


def find_link(s: str, index=0) -> typing.Optional[Link]:
    """
    Using the state machine, find the first Markdown link found in the string `s` after the `index` position.
    The following are considered links (alt text or title may be missing):
        - [title](/loca/ti/on "Alt text")
        - ![title](/path/to/image "Alt text), with ! not considered a part of the link
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


def find_reference(s: str) -> typing.Optional[typing.Tuple[str, str]]:
    """
    Given a line, attempt to extract a reference from it (assuming it occupies the whole line). Example:
        - "[reference]: /wiki/kudosu.png" -> ("reference", "/wiki/kudosu.png")
    """

    split = s.find(':')
    if split != -1 and s.startswith('[') and s[split - 1] == ']' and s[split + 1] == ' ':
        return (s[1:split - 1], s[split + 2:-1])


def find_references(file) -> References:
    """
    Attempt to read link references in form of "[reference_name]: /path/to/location" from a text file.
    """

    seek = file.tell()
    references = {}
    for linenumber, line in enumerate(file, start=1):
        reference = find_reference(line)
        if reference:
            references[reference[0]] = (reference[1], linenumber)
    file.seek(seek)
    return references
