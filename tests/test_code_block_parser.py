from wikitools import code_block_parser


class TestCodeBlockParser:
    def test__inclusion(self):
        # `` `t` ``
        assert code_block_parser.CodeBlock(start=0, closed_at=7, tag_len=2).contains(
            code_block_parser.CodeBlock(start=3, closed_at=5, tag_len=1)
        )

        # ` ``t`` `
        assert not code_block_parser.CodeBlock(start=0, closed_at=8, tag_len=1).contains(
            code_block_parser.CodeBlock(start=2, closed_at=5, tag_len=2)
        )

        # ``first`` `second` ``third``
        first = code_block_parser.CodeBlock(start=0, closed_at=7, tag_len=2)
        second = code_block_parser.CodeBlock(start=10, closed_at=17, tag_len=1)
        third = code_block_parser.CodeBlock(start=19, closed_at=26, tag_len=2)
        assert not first.contains(second) and not first.contains(third)
        assert not second.contains(first) and not second.contains(third)
        assert not third.contains(first) and not third.contains(second)

    def test__inline_blocks(self):
        for line, expected in (
            ("Empty", []),
            (
                "`test`",
                [code_block_parser.CodeBlock(start=0, closed_at=5, tag_len=1)]
            ),
            (
                "`several` `code blocks`",
                [
                    code_block_parser.CodeBlock(start=0, closed_at=8, tag_len=1),
                    code_block_parser.CodeBlock(start=10, closed_at=22, tag_len=1),
                ]
            ),
            (
                "``block-o``",
                [code_block_parser.CodeBlock(start=0, closed_at=9, tag_len=2)]
            ),
            (
                "`` `Space` ``",
                [code_block_parser.CodeBlock(start=0, closed_at=11, tag_len=2)]
            ),
        ):
            assert code_block_parser.CodeBlockParser().parse(line) == expected, line

    def test__multiline_blocks(self):
        lines = [
            "This is expected:",
            "```",
            "Failure!",
            "```",
            "And this is not: ```",
            "Success! `Your application has been approved` (or not)```",
        ]

        blocks = []
        parser = code_block_parser.CodeBlockParser()
        for line in lines:
            blocks.extend(parser.parse(line))

        assert blocks == [
            code_block_parser.CodeBlock(start=0, closed_at=-1, tag_len=3),
            code_block_parser.CodeBlock(start=-1, closed_at=-1, tag_len=3),
            code_block_parser.CodeBlock(start=-1, closed_at=0, tag_len=3),

            code_block_parser.CodeBlock(start=17, closed_at=-1, tag_len=3),
            code_block_parser.CodeBlock(start=-1, closed_at=54, tag_len=3),
        ]
