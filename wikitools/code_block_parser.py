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
        tag_stack: typing.List[CodeTag] = []
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
                blocks.append(CodeBlock(start=opening_tag.start, end=i + opening_tag.len - 1, tag_len=opening_tag.len))
            else:
                tag_stack.append(CodeTag(start=i, len=cnt))
            i += cnt

        if tag_stack:
            for t in tag_stack:
                if t.len == 3:
                    # Find if there is an open multiline code block somewhere,
                    # then discard everything that got inside and return the blocks we parsed before it
                    # Example: "``test`` ```abc `def`" is treated as code block with "test" and a multiline block
                    # where we don't care if `def` is inside or not as it is superseded anyway
                    self.__in_multiline = True
                    i = 0
                    while i < len(blocks) and blocks[i].start <= t.start:
                        i += 1
                    return blocks[0: i] + [CodeBlock(start=t.start, end=-1, tag_len=3)]

            # If there is no start of a multiline code block, it's a Markdown error (one or more inline blocks not closed)
            # Return what we could close
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
