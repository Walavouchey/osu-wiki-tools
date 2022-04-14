import typing


class Comment(typing.NamedTuple):
    """
    An HTML comment in a line.

    These mark regions where parsed content should be discarded.

    Example:
        <!-- this is a comment -->
        ^ start                  ^ end

    Multiline comments are expressed by setting the start and/or end
    values to -1, indicating continuation of a comment from a
    previous line or to subsequent lines respectively.

    Examples:

        A multiline comment continuing from a previous line -->
        (start = -1)                                          ^ end

        <!-- A multiline comment continuing off to subsequent lines
        ^ start                                          (end = -1)

        A whole line marked as part of a multiline comment
        (start = -1)                            (end = -1)
    """

    start: int
    end: int


def parse(line: str, in_multiline: bool = False) -> typing.List[Comment]:
    comments: typing.List[Comment] = []
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
