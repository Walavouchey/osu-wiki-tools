from wikitools import link_parser


class TestInlinePlainLinks:
    def test__regular_link(self):
        example = "An [example](/wiki/Example)."
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            link_start=3,
            link_end=26,
            title="example",
            location="/wiki/Example",
            extra="",
            is_reference=False,
        )

    def test__regular_link__alt_text(self):
        example = 'An [example](/wiki/Example "Alt text").'
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            link_start=3,
            link_end=37,
            title="example",
            location="/wiki/Example",
            extra=' "Alt text"',
            is_reference=False,
        )

    def test__no_link(self):
        example = 'Check this out: [[a]].'
        assert link_parser.find_links(example) == []

    def test__no_link__in_square_brackets(self):
        example = 'Check this out: [[a](/wiki/A)].'
        assert link_parser.find_links(example) == []

    def test__link__nested_brackets(self):
        example = 'Check this out: [a](/wiki/[A])].'
        assert link_parser.find_links(example) == [
            link_parser.Link(
                link_start=16,
                link_end=29,
                title="a",
                location="/wiki/[A]",
                extra="",
                is_reference=False,
            )
        ]

    def test__link__identifier(self):
        example = "RTF[M](/wiki/M#manual)."
        assert link_parser.find_link(example) == link_parser.Link(
            link_start=3,
            link_end=21,
            title="M",
            location="/wiki/M",
            extra="#manual",
            is_reference=False,
        )

    def test__link__query_string(self):
        example = "[example.com](https://example.com/?test=1) for sale!"
        assert link_parser.find_link(example) == link_parser.Link(
            link_start=0,
            link_end=41,
            title="example.com",
            location="https://example.com/",
            extra="?test=1",
            is_reference=False,
        )


class TestInlineImageLinks:
    def test__image_link(self):
        example = "Check this out: ![](/wiki/crown.png)"
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            link_start=17,
            link_end=35,
            title="",
            location="/wiki/crown.png",
            extra="",
            is_reference=False,
        )

    def test__image_link__title(self):
        example = "Check this out: ![Crown](/wiki/crown.png)"
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            link_start=17,
            link_end=40,
            title="Crown",
            location="/wiki/crown.png",
            extra="",
            is_reference=False,
        )

    def test__image_link__alt_text(self):
        example = 'Check this out: ![](/wiki/crown.png "Alt text")'
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            link_start=17,
            link_end=46,
            title="",
            location="/wiki/crown.png",
            extra=' "Alt text"',
            is_reference=False,
        )

    def test__image_link__title__alt_text(self):
        example = 'Check this out: ![Crown](/wiki/crown.png "Alt text")'
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            link_start=17,
            link_end=51,
            title="Crown",
            location="/wiki/crown.png",
            extra=' "Alt text"',
            is_reference=False,
        )


class TestInlineMultipleLinks:
    def test__multiple_links(self):
        example = 'Check this out: [a](/wiki/A) and [b](/wiki/B).'
        links = link_parser.find_links(example)
        assert links == [
            link_parser.Link(
                link_start=16,
                link_end=27,
                title="a",
                location="/wiki/A",
                extra="",
                is_reference=False,
            ),
            link_parser.Link(
                link_start=33,
                link_end=44,
                title="b",
                location="/wiki/B",
                extra="",
                is_reference=False,
            )
        ]


class TestReferenceLinks:
    def test__regular_link(self):
        example = "See for [yourself][reference]."
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            link_start=8,
            link_end=28,
            title="yourself",
            location="reference",
            extra="",
            is_reference=True,
        )

    def test__image_link(self):
        example = "No crowns here: ![Sweden][SE_flag]"
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            link_start=17,
            link_end=33,
            title="Sweden",
            location="SE_flag",
            extra="",
            is_reference=True,
        )
