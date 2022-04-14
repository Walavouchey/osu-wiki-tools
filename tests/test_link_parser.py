from urllib import parse

from wikitools import link_parser, reference_parser


class TestInlinePlainLinks:
    def test__regular_link(self):
        example = "An [example](/wiki/Example)."
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            start=3,
            end=26,
            alt_text="example",
            raw_location="/wiki/Example",
            parsed_location=parse.urlparse("/wiki/Example"),
            title="",
            is_reference=False,
        )

    def test__regular_link__title(self):
        example = 'An [example](/wiki/Example "Title").'
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            start=3,
            end=34,
            alt_text="example",
            raw_location="/wiki/Example",
            parsed_location=parse.urlparse("/wiki/Example"),
            title=' "Title"',
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
                start=16,
                end=29,
                alt_text="a",
                raw_location="/wiki/[A]",
                parsed_location=parse.urlparse("/wiki/[A]"),
                title="",
                is_reference=False,
            )
        ]

    def test__link__fragment(self):
        example = "RTF[M](/wiki/M#manual)."
        assert link_parser.find_link(example) == link_parser.Link(
            start=3,
            end=21,
            alt_text="M",
            raw_location="/wiki/M#manual",
            parsed_location=parse.urlparse("/wiki/M#manual"),
            title="",
            is_reference=False,
        )

    def test__link__query_string(self):
        example = "[example.com](https://example.com/?test=1) for sale!"
        assert link_parser.find_link(example) == link_parser.Link(
            start=0,
            end=41,
            alt_text="example.com",
            raw_location="https://example.com/?test=1",
            parsed_location=parse.urlparse("https://example.com/?test=1"),
            title="",
            is_reference=False,
        )


class TestInlineImageLinks:
    def test__image_link(self):
        example = "Check this out: ![](/wiki/crown.png)"
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            start=17,
            end=35,
            alt_text="",
            raw_location="/wiki/crown.png",
            parsed_location=parse.urlparse("/wiki/crown.png"),
            title="",
            is_reference=False,
        )

    def test__image_link__alt_text(self):
        example = "Check this out: ![Crown](/wiki/crown.png)"
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            start=17,
            end=40,
            alt_text="Crown",
            raw_location="/wiki/crown.png",
            parsed_location=parse.urlparse("/wiki/crown.png"),
            title="",
            is_reference=False,
        )

    def test__image_link__title(self):
        example = 'Check this out: ![](/wiki/crown.png "Title")'
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            start=17,
            end=43,
            alt_text="",
            raw_location="/wiki/crown.png",
            parsed_location=parse.urlparse("/wiki/crown.png"),
            title=' "Title"',
            is_reference=False,
        )

    def test__image_link__alt_text__title(self):
        example = 'Check this out: ![Crown](/wiki/crown.png "Title")'
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            start=17,
            end=48,
            alt_text="Crown",
            raw_location="/wiki/crown.png",
            parsed_location=parse.urlparse("/wiki/crown.png"),
            title=' "Title"',
            is_reference=False,
        )


class TestInlineMultipleLinks:
    def test__multiple_links(self):
        example = 'Check this out: [a](/wiki/A) and [b](/wiki/B).'
        links = link_parser.find_links(example)
        assert links == [
            link_parser.Link(
                start=16,
                end=27,
                alt_text="a",
                raw_location="/wiki/A",
                parsed_location=parse.urlparse("/wiki/A"),
                title="",
                is_reference=False,
            ),
            link_parser.Link(
                start=33,
                end=44,
                alt_text="b",
                raw_location="/wiki/B",
                parsed_location=parse.urlparse("/wiki/B"),
                title="",
                is_reference=False,
            )
        ]


class TestReferenceLinks:
    def test__regular_link(self):
        example = "See for [yourself][reference]."
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            start=8,
            end=28,
            alt_text="yourself",
            raw_location="reference",
            parsed_location=parse.urlparse("reference"),
            title="",
            is_reference=True,
        )

    def test__image_link(self):
        example = "No crowns here: ![Sweden][SE_flag]"
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            start=17,
            end=33,
            alt_text="Sweden",
            raw_location="SE_flag",
            parsed_location=parse.urlparse("SE_flag"),
            title="",
            is_reference=True,
        )


class TestIdentifierLinks:
    def test__misc_links(self):
        for example, (start, fragment_start) in (
            ("Thank you, we'll [call](/wiki/Test#test) your name", (17, 34)),
            ("I am sure you [will](#local-ref).", (14, 21)),
            ("No [reference](/wiki/No).", (3, 23)),
        ):
            link = link_parser.find_link(example)
            assert link.start == start
            assert link.fragment_start == fragment_start
            print(link.end)


class TestLinkObject:
    def test__resolution(self):
        for link, reference, (raw_location, parsed_location) in (
            ('This is an [example][example_ref].', '[example_ref]: https://example.com "Example"', ('https://example.com', parse.urlparse("https://example.com"))),
            ('Cats are cute. [[1]][r]', '[r]: #references', ('#references', parse.urlparse("#references"))),
        ):
            link = link_parser.find_link(link)
            reference = reference_parser.extract(reference, lineno=1)

            assert link.resolve({reference.name: reference}).raw_location == reference.raw_location
            assert link.resolve({reference.name: reference}).raw_location == raw_location
            assert link.resolve({reference.name: reference}).parsed_location == reference.parsed_location
            assert link.resolve({reference.name: reference}).parsed_location == parsed_location
        assert link.resolve({}) is None
