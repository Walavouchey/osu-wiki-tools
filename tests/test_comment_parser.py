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
            assert comment_parser.CommentParser().parse(line) == expected

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
        parser = comment_parser.CommentParser()
        for line in lines:
            comments.extend(parser.parse(line))

        assert comments == [
            comment_parser.Comment(start=10, end=-1),
            comment_parser.Comment(start=-1, end=-1),
            comment_parser.Comment(start=-1, end=-1),
            comment_parser.Comment(start=-1, end=12),
            comment_parser.Comment(start=22, end=34),
            comment_parser.Comment(start=0, end=-1),
            comment_parser.Comment(start=-1, end=11),
        ]
