import argparse
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
    A Markdown link, external or internal. May be relative. Example:

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
        return f"[{self.title}]({self.content})"

    @property
    def full_coloured_link(self):
        return "{title_in_braces}{left_brace}{location}{extra}{right_brace}".format(
            title_in_braces=green(f"[{self.title}]"),
            left_brace=green('('),
            location=red(self.location),
            extra=blue(self.extra),
            right_brace=green(')'),
        )


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


def find_comments(line: str, in_multiline: bool) -> typing.List[Comment]:
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


def find_link(s: str, index=0) -> typing.Optional[Link]:
    found_brackets = False
    started = False
    start = None
    mid = None
    extra = None
    end = None
    square_bracket_level = 0
    parenthesis_level = 0
    for i, c in enumerate(s[index:]):
        i += index
        if not found_brackets and c == '[':
            if not started:
                start = i
                started = True
            square_bracket_level += 1
            continue
        if started and not found_brackets and c == ']':
            square_bracket_level -= 1
            if square_bracket_level == 0:
                if len(s) > i + 1 and s[i + 1] == '(':
                    found_brackets = True
                    mid = i + 1
            continue
        if found_brackets and (c == ' ' or c == '#' or c == '?'):
            if extra is None:
                extra = i
            continue
        if found_brackets and c == '(':
            parenthesis_level += 1
            continue
        if found_brackets and c == ')':
            parenthesis_level -= 1
            if parenthesis_level == 0:
                end = i
                if extra is None:
                    extra = end

                return Link(
                    location=s[mid + 1: extra],
                    title=s[start + 1: mid - 1],
                    extra=s[extra: end],
                    link_start=start,
                    link_end=end,
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


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--target", nargs='*', help="paths to the articles you want to check")
    parser.add_argument("-a", "--all", action='store_true', help="check all articles")
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

        with open(filename, 'r', encoding='utf-8') as fd:
            in_multiline = False
            for linenumber, line in enumerate(fd, start=1):
                comments = find_comments(line, in_multiline)
                if comments:
                    in_multiline = comments[-1].end == -1

                for match in find_links(line):
                    if is_in_comment(match.link_start, comments):
                        continue

                    if match.content == "/wiki/Sitemap":
                        continue
                    success, note = check_link(redirects, directory(filename), match.location)
                    if success:
                        continue

                    if exit_code == 0:
                        print_error()
                    exit_code = 1

                    print(f"{yellow(filename)}:{linenumber}:{match.link_start + 1}: {red(match.location)}")
                    if note:
                        print(note)

                    print("{}{}{}".format(line[:match.link_start], match.full_coloured_link, line[match.link_end + 1:]), end="\n\n")

    if exit_code == 0:
        print_clean()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
