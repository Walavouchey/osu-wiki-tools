from wikitools import code_block_parser


class TestCodeBlockParser:
    def test__inline_blocks(self):
        for line, expected in (
            ("Empty", []),
            (
                "`test`",
                [code_block_parser.CodeBlock(start=0, end=5)]
            ),
            (
                "`several` `code blocks`",
                [
                    code_block_parser.CodeBlock(start=0, end=8),
                    code_block_parser.CodeBlock(start=10, end=22),
                ]
            ),
            (
                "``block-o``",
                [code_block_parser.CodeBlock(start=0, end=10)]
            ),
            (
                "`` `Space` ``",
                [code_block_parser.CodeBlock(start=0, end=12)]
            ),
            (
                "`` code block with random backticks ` ``` ` ``` ``",
                [code_block_parser.CodeBlock(start=0, end=49)]
            ),
            (
                "stray backtick ` and a ``code block`` and another stray ```",
                [code_block_parser.CodeBlock(start=23, end=36)]
            ),
        ):
            parser = code_block_parser.CodeBlockParser()
            assert parser.parse(line) == expected, line
            assert not parser.in_multiline

    def test__multiline_blocks(self):
        lines = [
            "This is expected:",
            "```",
            "Valid code block",
            "```",
            "````markdown",
            "```",
            "Code block inside code block (ignored)",
            "Inline `code blocks` inside a code block",
            "```",
            "````",
            "This won't start a multi-line code block: ```",
            "Here we have a `valid in-line code block`",
            "```",
            "Trailing multi-line code block",
        ]

        blocks = []
        parser = code_block_parser.CodeBlockParser()
        for line in lines:
            blocks.extend(parser.parse(line))

        assert blocks == [
            *(9 * [code_block_parser.CodeBlock(start=-1, end=-1)]),

            code_block_parser.CodeBlock(start=15, end=40),
            code_block_parser.CodeBlock(start=-1, end=-1),
            code_block_parser.CodeBlock(start=-1, end=-1),
        ]
        assert parser.in_multiline
