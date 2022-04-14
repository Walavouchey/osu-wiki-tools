import typing


class CodeTag(typing.NamedTuple):
    start: int
    len: int


class CodeBlock(typing.NamedTuple):
    """
    A Markdown code block (monospace font + gray backround). Could be one of the following:
        - Inline: `text` or `` text `` (the latter is used for snippets containing `)
        - Multiline: ``` followed by anything else until the next ``` block

    Examples:

        ```test test test```
        ^ start            ^ end

        `this is a very long phrase`
        ^ start                    ^ end

    Similarly to the HTML comments, links in code blocks are not accounted for.
    """

    start: int  # 0-based position of the first character of the block's opening tag
    end: int  # 0-based position of the last character of the block's closing tag
    tag_len: int

    @property
    def is_multiline(self):
        return self.end == -1 and self.tag_len == 3

    def contains(self, other: 'CodeBlock'):
        return (
            self.start < other.start and
            self.end > other.end and
            self.tag_len > other.tag_len
        )


class CodeBlockParser:
    def __init__(self):
        self.__in_multiline = False

    @property
    def in_multiline(self) -> bool:
        return self.__in_multiline

    def parse(self, line: str) -> typing.List[CodeBlock]:
        blocks: typing.List[CodeBlock] = []

        tag_stack = []
        if self.__in_multiline:
            tag_stack.append(CodeTag(start=-1, len=3))

        i = 0
        while i < len(line):
            if line[i] != '`':
                i += 1
                continue

            cnt = 0
            while i + cnt < len(line) and line[i + cnt] == '`':
                cnt += 1

            # just closed the code block
            if tag_stack and tag_stack[-1].len == cnt:
                opening_tag = tag_stack.pop()
                # add the new code block
                # if it's mistakenly included into a smaller one (` ```test``` `), remark will catch that anyway
                blocks.append(CodeBlock(start=opening_tag.start, end=i + opening_tag.len - 1, tag_len=opening_tag.len))
            else:
                tag_stack.append(CodeTag(start=i, len=cnt))
            i += cnt

        if tag_stack:
            opening_tag = tag_stack[0]
            # if there is a start of the multiline code block, the block takes priority over everything else
            if opening_tag.len == 3:
                self.__in_multiline = True
                return [CodeBlock(start=opening_tag.start, end=-1, tag_len=3)]
            # one of the inline blocks wasn't closed, which will be caught by a Markdown linter anyway
            else:
                self.__in_multiline = blocks and blocks[0].is_multiline
                return blocks

        # if all tags are closed, we need to consider that larger code blocks consume smaller ones
        filtered_blocks: typing.List[CodeBlock] = []
        blocks.sort()
        i = 0
        while i < len(blocks):
            filtered_blocks.append(blocks[i])
            i += 1
            while i < len(blocks) and filtered_blocks[-1].contains(blocks[i]):
                i += 1

        self.__in_multiline = filtered_blocks and filtered_blocks[0].is_multiline
        return filtered_blocks


def is_in_code_block(link_start: int, code_blocks: typing.List[CodeBlock]) -> bool:
    if (
        not code_blocks or
        link_start < code_blocks[0].start or
        link_start > code_blocks[-1].end
    ):
        return False

    for block in code_blocks:
        if (
            block.start < link_start < block.end or
            block.start < link_start and block.is_multiline
        ):
            return True

    return False
