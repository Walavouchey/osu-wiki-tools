import enum
import os
import typing
from urllib import parse

from wikitools import console, redirect_parser, errors


class Reference(typing.NamedTuple):
    lineno: int
    name: str
    raw_location: str
    parsed_location: parse.ParseResult
    alt_text: str

    @property
    def start(self):
        return 0

    @classmethod
    def parse(cls, s: str, lineno) -> typing.Optional['Reference']:
        """
        Given a line, attempt to extract a reference from it (assuming it occupies the whole line). Example:
            - "[reference]: /wiki/kudosu.png" -> ("reference", "/wiki/kudosu.png")
        """

        split = s.find(':')
        if split != -1 and s.startswith('[') and s[split - 1] == ']' and s[split + 1] == ' ':
            name = s[1:split - 1]
            try:
                location, alt_text = s[split + 2:].split(' ', maxsplit=1)
                alt_text = alt_text[1:-1]  # trim quotes
            except ValueError:  # no space
                location = s[split + 2:]
                alt_text = ""

            parsed_location = parse.urlparse(location)
            return cls(
                lineno=lineno, name=name,
                raw_location=location, parsed_location=parsed_location, alt_text=alt_text
            )


References = typing.Dict[str, Reference]


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

    def resolve(self, references: References) -> typing.Union['Link', typing.Optional[Reference]]:
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


def extract_tail(path: str) -> str:
    """
    Given a path in a file system, return its tail (everything past the first non-root slash). Examples:
        - /wiki/Beatmap/Category -> Beatmap/Category
        - img/users/2.png -> users/2.png
    """
    return path[path.find('/', 1) + 1:]


def check_link(
    redirects: redirect_parser.Redirects, references: References, current_article_dir: str,
    link_: typing.Union[Link, Reference]
) -> typing.Optional[errors.LinkError]:
    """
    Verify that the link is valid:
        - External links are always assumed valid, since we can't just issue HTTP requests left and right
        - For Markdown references, there exists a dereferencing line with [reference_name]: /lo/ca/ti/on
        - Direct internal links, as well as redirects, must point to existing article files
        - Relative links are parsed under the assumption that
            their parent (current article, where the link is defined) is `directory`
    """

    # resolve the link, if possible
    link = link_ if isinstance(link_, Reference) else link_.resolve(references)
    if link is None:
        return errors.MissingReference(link_.raw_location)

    location = link.parsed_location.path
    parsed_location = link.parsed_location

    # some external link; don't care
    if parsed_location.scheme:
        return

    # internal link (domain is empty)
    if parsed_location.netloc == '':
        # convert a relative wikilink to absolute
        if not location.startswith("/wiki/"):
            location = f"/wiki/{current_article_dir}/{location}"

        # article file exists -> quick win
        # TODO(TicClick): check if a section exists
        if os.path.exists(location[1:]):
            return

        # check for a redirect
        redirect_source = extract_tail(location)
        try:
            redirect_destination, redirect_line_no = redirects[redirect_source.lower()]
        except KeyError:
            return errors.LinkNotFound(redirect_source)

        if not os.path.exists(f"wiki/{redirect_destination}"):
            return errors.BrokenRedirect(redirect_source, redirect_line_no, redirect_destination)

    else:
        raise RuntimeError(f"Unhandled link type: {parsed_location}")


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


def find_references(text) -> References:
    """
    Attempt to read link references in form of "[reference_name]: /path/to/location" from a text file.
    """

    references = (
        Reference.parse(line, lineno)
        for lineno, line in enumerate(text.splitlines(), start=1)
    )
    return {
        r.name: r
        for r in references if
        r is not None
    }
