import typing
from functools import lru_cache
from urllib import parse
import textwrap

from wikitools import console, reference_parser

_urlparse = lru_cache(maxsize=4096)(parse.urlparse)


# Not an enum/class to avoid attribute lookups
_STATE_IDLE = 0  # IDLE: jump to next '[' using optimized str.find
_STATE_START = 1  # START: tracking bracket depth inline
_STATE_INLINE = 2  # INLINE: tracking paren depth inline
_STATE_REFERENCE = 3  # REFERENCE: tracking bracket depth inline


def _shorten(s):
    return textwrap.shorten(s, 20, placeholder="...")


class Link(typing.NamedTuple):
    """
    A Markdown link, inline- or reference-style, external or internal.
    May be relative. Example:

        See [Difficulty Names](/wiki/Beatmap/Difficulty#naming-conventions)

    - alt_text: 'Difficulty Names'
    - raw_location: '/wiki/Beatmap/Difficulty#naming-conventions'
    - parsed_location: urllib.parse.ParseResult with all of its fields

    Another example:

        ![Player is AFK](img/chat-console-afk.png "Player is away from keyboard")

    - alt_text: 'Player is AFK'
    - raw_location: 'img/chat-console-afk.png'
    - parsed_location: urllib.parse.ParseResult with all of its fields
    - title: ' "Player is away from keyboard"'
    """

    # Link position within the line. Example:
    #   See also: [Difficulty names](/wiki/Beatmap/Difficulty#naming-conventions)
    #             ^ start                                                       ^ end
    start: int
    end: int

    # Sections of a link. Example:
    #    ![Player is AFK](img/chat-console-afk.png "Player is away from keyboard")
    #      ^ alt_text  ^
    #                     ^ ----- location ----- ^
    #                                             ^ ---------- title ---------- ^
    #                     ^ --------------------- content --------------------- ^
    #     ^ ------------------ full_link / full_coloured_link ------------------ ^
    alt_text: str
    raw_location: str
    parsed_location: parse.ParseResult
    title: str

    @property
    def content(self):
        return self.raw_location if not self.title else f"{self.raw_location} {self.title}"

    @property
    def full_link(self):
        if self.is_reference:
            return f"[{self.alt_text}][{self.content}]"
        else:
            return f"[{self.alt_text}]({self.content})"

    @property
    def truncated_coloured_link(self, fragment_only=False):
        return "{alt_text_in_braces}{left_brace}{location}{extra}{right_brace}".format(
            alt_text_in_braces=console.green(f"[{_shorten(self.alt_text)}]"),
            left_brace=console.green('[') if self.is_reference else console.green('('),
            location=self.colourise_location(),
            extra=" " + console.blue("\"...\"") if self.title else "",
            right_brace=console.green(']') if self.is_reference else console.green(')'),
        )

    @property
    def truncated_coloured_link_fragment(self, fragment_only=False):
        return "{alt_text_in_braces}{left_brace}{location}{extra}{right_brace}".format(
            alt_text_in_braces=console.green(f"[{_shorten(self.alt_text)}]"),
            left_brace=console.green('[') if self.is_reference else console.green('('),
            location=self.colourise_location(fragment_only=True),
            extra=" " + console.blue("\"...\"") if self.title else "",
            right_brace=console.green(']') if self.is_reference else console.green(')'),
        )

    @property
    def fragment_start(self):
        """
        Position of the link #fragment in the line, if there is one. Otherwise, the same value as the end of the link.
        """
        return self.start + len(self.alt_text) + 2 + len(self.parsed_location.path) + 1

    def colourise_link(self, fragment_only=False):
        return "{alt_text_in_braces}{left_brace}{location}{extra}{right_brace}".format(
            alt_text_in_braces=console.green(f"[{self.alt_text}]"),
            left_brace=console.green('[') if self.is_reference else console.green('('),
            location=self.colourise_location(fragment_only=fragment_only),
            extra=" " + console.blue(self.title) if self.title else "",
            right_brace=console.green(']') if self.is_reference else console.green(')'),
        )

    def colourise_location(self, fragment_only=False):
        return self.colourise_location_static(self.raw_location.split("#")[0], self.parsed_location.fragment, fragment_only=fragment_only)

    # provided for convenience, used in `BrokenRedirectError`
    @staticmethod
    def colourise_location_static(location: str, fragment: typing.Optional[str] = None, fragment_only: bool = False):
        if fragment_only:
            colourised_location = console.green(location)
            if fragment:
                colourised_location += console.red('#' + fragment)
            return colourised_location
        return console.red(location + ('#' + fragment if fragment else ""))

    def resolve(
        self, references: reference_parser.References
    ) -> typing.Optional[reference_parser.Reference]:
        if not self.is_reference:
            return None
        return references.get(self.parsed_location.path)

    # Whether the link is a reference-style link. The only difference is that
    # `location` is a reference and needs to be resolved later.
    #
    # The syntax for such links is the almost the same as regular links:
    #    [text][reference]
    #
    # The reference can then later be defined at the start of a new line:
    #    [reference]: link
    is_reference: bool


def find_link(s: str, index=0) -> typing.Optional[Link]:
    """
    Finds the first valid Markdown link found in the string `s`, starting the search from position `index`.
    The following are considered links (title and alt text may be omitted):
        - [alt_text](/loca/ti/on "Title")
        - ![alt_text](/path/to/image "Title), with ! not being considered a part of the link
        - [artist - title (creator) [diff]](/loca/ti/ion_(with_parentheses) "Title")
        - [alt_text][reference], with exact locations found separately via find_reference()
    """

    state = _STATE_IDLE

    start = -1
    location = -1
    extra = None

    in_leading_whitespace = True

    bracket_depth = 0
    paren_depth = 0

    s_len = len(s)
    i = index

    while i < s_len:
        if state == _STATE_IDLE:
            i = s.find('[', i)
            if i == -1:
                return None

            # potential start of a link
            bracket_depth = 1
            state = _STATE_START
            start = i
            i += 1
            continue

        c = s[i]

        if state == _STATE_START:
            if c == '[':
                bracket_depth += 1
            elif c == ']':
                bracket_depth -= 1
            if bracket_depth == 0:
                if s_len <= i + 1:
                    # end of the line
                    state = _STATE_IDLE
                    i += 1
                    continue

                if s[start + 1] == '^':
                    # found a footnote -> ignore
                    state = _STATE_IDLE
                    i += 1
                    continue

                # the end of a bracket. the link may continue
                # to be inline- or reference-style
                if s[i + 1] == '(':
                    state = _STATE_INLINE
                    location = i + 2
                    paren_depth = 0
                elif s[i + 1] == '[':
                    if i + 2 < s_len and s[i + 2] == '^':
                        # found a footnote after bracket pair -> ignore
                        state = _STATE_IDLE
                        i += 1
                        continue

                    state = _STATE_REFERENCE
                    location = i + 2
                    bracket_depth = 0
                else:
                    state = _STATE_IDLE
            i += 1
            continue

        if state == _STATE_INLINE:
            if c == ' ' and not in_leading_whitespace and extra is None:
                extra = i
            elif c != ' ' and in_leading_whitespace and paren_depth > 0:
                in_leading_whitespace = False

            if c == '(':
                paren_depth += 1
            elif c == ')':
                paren_depth -= 1
            if paren_depth == 0:
                # end of a complete link
                if extra is None:
                    extra = i

                raw_location = s[location: extra]
                return Link(
                    raw_location=raw_location,
                    parsed_location=_urlparse(raw_location.strip()),
                    alt_text=s[start + 1: location - 2],
                    title=s[extra: i],
                    start=start,
                    end=i,
                    is_reference=False
                )
            i += 1
            continue

        if state == _STATE_REFERENCE:
            if c == '[':
                bracket_depth += 1
            elif c == ']':
                bracket_depth -= 1
            if bracket_depth == 0:
                # end of a complete reference-style link
                raw_location = s[location: i]
                return Link(
                    raw_location=raw_location,
                    parsed_location=_urlparse(raw_location),
                    alt_text=s[start + 1: location - 2],
                    title="",
                    start=start,
                    end=i,
                    is_reference=True
                )
            i += 1
            continue

        i += 1

    return None


def find_links(line: str) -> typing.List[Link]:
    """
    Iteratively extract all links from a line.
    """

    if '[' not in line:
        return []

    results = []
    match = find_link(line)
    while match:
        results.append(match)
        match = find_link(line, match.end + 1)
    return results
