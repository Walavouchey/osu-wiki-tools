import argparse
from enum import Enum
import os
import sys
import typing


Redirects = typing.Dict[str, typing.Tuple[str, int]]


class Comment(typing.NamedTuple):
    """
    An HTML comment in a line.

    These mark regions where parsed content should be discarded.

    Example:
        <!-- this is a comment -->
        ^ start                  ^ end

    Since an article is read and errors are printed line-by-line
    (to protect against unexpected crashes), multiline comments are
    expressed by setting the start and/or end values to -1, indicating
    continuation of a comment from a previous line or to subsequent
    lines respectively.

    Examples:

        A multiline comment continuing from a previous line -->
        (start = -1)                                          ^ end

        <!-- A multiline comment continuing off to subsequent lines
        ^ start                                          (end = -1)

        A whole line marked as part of a multiline comment
        (start = -1)                          (end = -1)
    """

    start: int
    end: int

class Link(typing.NamedTuple):
    """
    A Markdown link, inline- or reference-style, external or internal.
    May be relative. Example:

        See [Difficulty Names](/wiki/Beatmap/Difficulty#naming-conventions)

    - title: 'Difficulty Names'
    - location: '/wiki/Beatmap/Difficulty'
    - extra: '#naming-conventions'

    Another example:

        ![Player is AFK](img/chat-console-afk.png "Player is away from keyboard")

    - title: 'Player is AFK'
    - location: 'img/chat-console-afk.png'
    - extra: ' "Player is away from keyboard"'
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
    #                                             ^ ---------- extra ---------- ^
    #                     ^ --------------------- content --------------------- ^
    #     ^ ------------------ full_link / full_coloured_link ------------------ ^
    title: str
    location: str
    extra: str

    @property
    def content(self):
        return self.location + self.extra

    @property
    def full_link(self):
        if self.is_reference:
            return f"[{self.title}][{self.content}]"
        else:
            return f"[{self.title}]({self.content})"

    @property
    def full_coloured_link(self):
        return "{title_in_braces}{left_brace}{location}{extra}{right_brace}".format(
            title_in_braces=green(f"[{self.title}]"),
            left_brace= green('[') if self.is_reference else green('('),
            location=red(self.location),
            extra=blue(self.extra),
            right_brace=green(']') if self.is_reference else green(')'),
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


def red(s):
    return f"\x1b[31m{s}\x1b[0m"


def green(s):
    return f"\x1b[32m{s}\x1b[0m"


def yellow(s):
    return f"\x1b[33m{s}\x1b[0m"


def blue(s):
    return f"\x1b[34m{s}\x1b[0m"


def load_redirects(path: str) -> Redirects:
    redirects = {}
    with open(path, 'r', encoding='utf-8') as fd:
        for line_number, line in enumerate(fd, start=1):
            split = line.split('"')
            try:
                redirects[split[1]] = (split[3], line_number)
            except IndexError:
                pass
    return redirects


def child(path: str) -> str:
    return path[path.find('/', 1) + 1:]


def directory(filename: str) -> str:
    return filename[filename.find('/') + 1:filename.rfind('/')]


def check_redirect(redirects: Redirects, link: str):
    link = link.lower()
    try:
        destination, line_no = redirects[link]
    except KeyError:
        return (False, "")
    if not os.path.exists(f"wiki/{destination}"):
        note = f"{blue('Note:')} Broken redirect (redirect.yaml:{line_no}: {link} --> {destination})"
        return (False, note)
    return (True, "")


def check_link(redirects: Redirects, directory: str, link: str) -> typing.Tuple[bool, str]:
    if link.startswith("/wiki/"):
        # absolute wikilink
        if os.path.exists(link[1:]):
            return (True, "")
        else:
            # may have a redirect
            return check_redirect(redirects, child(link))
    elif not any(link.startswith(prefix) for prefix in ("http://", "https://", "mailto:")):
        # relative wikilink
        if os.path.exists(f"wiki/{directory}/{link}"):
            return (True, "")
        else:
            # may have a redirect
            return check_redirect(redirects, f"{directory}/{link}")
    else:
        # some other link; don't care
        return (True, "")


def find_comments(line: str, in_multiline: bool=False) -> typing.List[Comment]:
    comments = []
    index = 0
    start = None

    while True:
        # don't start a comment if already in one
        if not in_multiline:
            start = line.find("<!--", index)
            if start == -1:
                # no more comments
                return comments

        end = line.find("-->", start or 0)

        if end != -1:
            # found the end of a comment
            if in_multiline:
                # end of a multiline comment
                comments.append(Comment(start=-1, end=end + 2))
                in_multiline = False
            else:
                # whole inline comment
                comments.append(Comment(start=start, end=end + 2))
            index = end + 3
            continue
        elif start is None:
            # no comment start or end; the whole line is part of a comment
            comments.append(Comment(start=-1, end=-1))
            return comments
        else:
            # unmatched comment start: continuing to subsequent lines
            comments.append(Comment(start=start, end=-1))
            return comments


def is_in_comment(index: int, comments: typing.List[Comment]) -> bool:
    for comment in comments:
        left_bound = comment.start
        right_bound = comment.end
        if comment.start == -1:
            left_bound = float('-inf')
        if comment.end == -1:
            right_bound = float('inf')

        if index >= left_bound and index <= right_bound:
            return True

    return False


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

class State(Enum):
    IDLE = 0
    START = 1
    INLINE = 2
    REFERENCE = 3

def find_link(s: str, index=0) -> typing.Optional[Link]:
    state = State.IDLE

    start = None
    location = None
    extra = None
    end = None

    parens = Brackets('(', ')')
    brackets = Brackets('[', ']')

    for i, c in enumerate(s[index:]):
        i += index

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
            if (c == ' ' or c == '#' or c == '?'):
                if extra is None:
                    # start of extra part
                    extra = i

            if parens.closed(c):
                # end of a complete link
                end = i
                if extra is None:
                    extra = end

                return Link(
                    location=s[location: extra],
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
                    location=s[location: end],
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


def print_error():
    print(f"{red('Error:')} Some wiki or image links in the files you've changed have errors.\n")
    print("This can happen in one of the following ways:\n")
    print("- The article or image that the link points to has since been moved or renamed (make sure to match capitalisation)")
    print("- The link simply contains typos or formatting errors")
    print("- The link works, but contains locale selection (e.g. /wiki/en/Article_styling_criteria instead of /wiki/Article_styling_criteria)")
    print("- The link works, but contains URL-escaped characters (https://en.wikipedia.org/wiki/Percent-encoding). This only applies for links to articles and images inside the wiki.")
    print("- The link works, but incurs multiple redirects. Use a direct link instead.")
    print("\nFor more information on link style, see https://osu.ppy.sh/wiki/en/Article_styling_criteria/Formatting#links.\n")


def print_clean():
    print("Notice: No broken wiki or image links detected.")


def s(i: int, s: str) -> str:
    return f"{i} {s}{'s' if i != 1 else ''}"


def print_count(errors: int, matches: int, error_files: int, files: int):
    print(f"{blue('Note:')} Found {s(errors, 'error')} in {s(error_files, 'file')} ({s(matches, 'link')} in {s(files, 'file')} checked).")


def highlight_links(s: str, links: typing.List[Link]) -> str:
    highlighted_line = ""
    prev_index = 0
    for link in links:
        highlighted_line += s[prev_index:link.link_start]
        highlighted_line += link.full_coloured_link
        prev_index = link.link_end + 1
    highlighted_line += s[prev_index:-1]
    return highlighted_line


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--target", nargs='*', help="paths to the articles you want to check")
    parser.add_argument("-a", "--all", action='store_true', help="check all articles")
    parser.add_argument("-s", "--separate", action='store_true', help="print errors that appear on the same line separately")
    return parser.parse_args(args)


def file_iterator(roots: list):
    for item in roots:
        if os.path.isdir(item):
            for root, _, filenames in os.walk(item):
                for f in filenames:
                    filepath = os.path.join(root, f)
                    yield filepath
        elif os.path.isfile(item):
            yield item


def main():
    args = parse_args(sys.argv[1:])
    if not args.target and not args.all:
        print("Notice: No articles to check.")
        sys.exit(0)

    filenames = []
    if args.all:
        filenames = file_iterator(["wiki", "news"])
    else:
        filenames = args.target

    redirects = load_redirects("wiki/redirect.yaml")
    exit_code = 0
    error_count = 0
    match_count = 0
    error_file_count = 0
    file_count = 0
    for filename in filenames:
        filename = filename.replace('\\', '/')
        if filename.startswith("./"):
            filename = filename[2:]
        if any((
            not filename.endswith(".md"),
            "TEMPLATE" in filename,
            "README" in filename,
            "Article_styling_criteria" in filename,
        )):
            continue

        file_count += 1
        with open(filename, 'r', encoding='utf-8') as fd:
            in_multiline = False
            for linenumber, line in enumerate(fd, start=1):
                comments = find_comments(line, in_multiline)
                if comments:
                    in_multiline = comments[-1].end == -1

                matches = find_links(line)
                bad_links = []
                for match in matches:
                    if is_in_comment(match.link_start, comments):
                        continue
                    match_count += 1

                    if match.content == "/wiki/Sitemap":
                        continue

                    success, note = check_link(redirects, directory(filename), match.location)
                    if success:
                        continue
                    error_count += 1
                    bad_links.append(match)

                    if exit_code == 0:
                        print_error()
                    exit_code = 1

                    print(f"{yellow(filename)}:{linenumber}:{match.link_start + 1}: {red(match.location)}")
                    if note:
                        print(note)

                if bad_links:
                    error_file_count += 1
                    if args.separate:
                        for link in bad_links:
                            print(highlight_links(line, [link]), end="\n\n")
                    else:
                        print(highlight_links(line, bad_links), end="\n\n")

    if exit_code == 0:
        print_clean()
        print()
        print_count(error_count, match_count, error_file_count, file_count)
    else:
        print_count(error_count, match_count, error_file_count, file_count)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
