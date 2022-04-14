from wikitools import code_block_parser


class TestCodeBlockParser:
    def test__inclusion(self):
        # `` `t` ``
        assert code_block_parser.CodeBlock(start=0, closed_at=7, tag_len=2).contains(
            code_block_parser.CodeBlock(start=3, closed_at=5, tag_len=1)
        )

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
            assert code_block_parser.parse(line) == expected, line

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
        # TODO: this is copied from article_parser.parse() while it should be a standalone piece of code
        in_multiline = False
        for line in lines:
            new_blocks = code_block_parser.parse(line, in_multiline)
            if new_blocks:
                in_multiline = new_blocks[-1].end == -1
            blocks.extend(new_blocks)

        assert blocks == [
            code_block_parser.CodeBlock(start=0, closed_at=-1, tag_len=3),
            code_block_parser.CodeBlock(start=-1, closed_at=-1, tag_len=3),
            code_block_parser.CodeBlock(start=-1, closed_at=0, tag_len=3),

            code_block_parser.CodeBlock(start=17, closed_at=-1, tag_len=3),
            code_block_parser.CodeBlock(start=-1, closed_at=54, tag_len=3),
        ]
