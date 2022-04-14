from wikitools import comment_parser


class TestCommentParser:
    def test__inline_comments(self):
        for line, expected in (
            ("Empty", []),
            (
                "<!-- A single comment-->",
                [comment_parser.Comment(start=0, end=23)]
            ),
            (
                "<!-- Several --><!-- comments -->",
                [
                    comment_parser.Comment(start=0, end=15),
                    comment_parser.Comment(start=16, end=32),
                ]
            ),
        ):
            assert comment_parser.parse(line) == expected

    def test__multiline_comments(self):
        lines = [
            "I know my <!-- A",
            "B",
            "C",
            "and other --> letters.<!-- test -->",
            "Take a break",
            "<!-- and",
            "continue -->",
        ]

        comments = []
        # TODO: this is copied from article_parser.parse() while it should be a standalone piece of code
        in_multiline = False
        for line in lines:
            new_comments = comment_parser.parse(line, in_multiline)
            if new_comments:
                in_multiline = new_comments[-1].end == -1
            comments.extend(new_comments)

        assert comments == [
            comment_parser.Comment(start=10, end=-1),
            comment_parser.Comment(start=-1, end=-1),
            comment_parser.Comment(start=-1, end=-1),
            comment_parser.Comment(start=-1, end=12),
            comment_parser.Comment(start=22, end=34),
            comment_parser.Comment(start=0, end=-1),
            comment_parser.Comment(start=-1, end=11),
        ]
