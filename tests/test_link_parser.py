import textwrap
from urllib import parse

from wikitools import link_parser


class TestInlinePlainLinks:
    def test__regular_link(self):
        example = "An [example](/wiki/Example)."
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            start=3,
            end=26,
            title="example",
            raw_location="/wiki/Example",
            parsed_location=parse.urlparse("/wiki/Example"),
            alt_text="",
            is_reference=False,
        )

    def test__regular_link__alt_text(self):
        example = 'An [example](/wiki/Example "Alt text").'
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            start=3,
            end=37,
            title="example",
            raw_location="/wiki/Example",
            parsed_location=parse.urlparse("/wiki/Example"),
            alt_text=' "Alt text"',
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
                title="a",
                raw_location="/wiki/[A]",
                parsed_location=parse.urlparse("/wiki/[A]"),
                alt_text="",
                is_reference=False,
            )
        ]

    def test__link__fragment(self):
        example = "RTF[M](/wiki/M#manual)."
        assert link_parser.find_link(example) == link_parser.Link(
            start=3,
            end=21,
            title="M",
            raw_location="/wiki/M#manual",
            parsed_location=parse.urlparse("/wiki/M#manual"),
            alt_text="",
            is_reference=False,
        )

    def test__link__query_string(self):
        example = "[example.com](https://example.com/?test=1) for sale!"
        assert link_parser.find_link(example) == link_parser.Link(
            start=0,
            end=41,
            title="example.com",
            raw_location="https://example.com/?test=1",
            parsed_location=parse.urlparse("https://example.com/?test=1"),
            alt_text="",
            is_reference=False,
        )


class TestInlineImageLinks:
    def test__image_link(self):
        example = "Check this out: ![](/wiki/crown.png)"
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            start=17,
            end=35,
            title="",
            raw_location="/wiki/crown.png",
            parsed_location=parse.urlparse("/wiki/crown.png"),
            alt_text="",
            is_reference=False,
        )

    def test__image_link__title(self):
        example = "Check this out: ![Crown](/wiki/crown.png)"
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            start=17,
            end=40,
            title="Crown",
            raw_location="/wiki/crown.png",
            parsed_location=parse.urlparse("/wiki/crown.png"),
            alt_text="",
            is_reference=False,
        )

    def test__image_link__alt_text(self):
        example = 'Check this out: ![](/wiki/crown.png "Alt text")'
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            start=17,
            end=46,
            title="",
            raw_location="/wiki/crown.png",
            parsed_location=parse.urlparse("/wiki/crown.png"),
            alt_text=' "Alt text"',
            is_reference=False,
        )

    def test__image_link__title__alt_text(self):
        example = 'Check this out: ![Crown](/wiki/crown.png "Alt text")'
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            start=17,
            end=51,
            title="Crown",
            raw_location="/wiki/crown.png",
            parsed_location=parse.urlparse("/wiki/crown.png"),
            alt_text=' "Alt text"',
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
                title="a",
                raw_location="/wiki/A",
                parsed_location=parse.urlparse("/wiki/A"),
                alt_text="",
                is_reference=False,
            ),
            link_parser.Link(
                start=33,
                end=44,
                title="b",
                raw_location="/wiki/B",
                parsed_location=parse.urlparse("/wiki/B"),
                alt_text="",
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
            title="yourself",
            raw_location="reference",
            parsed_location=parse.urlparse("reference"),
            alt_text="",
            is_reference=True,
        )

    def test__image_link(self):
        example = "No crowns here: ![Sweden][SE_flag]"
        link = link_parser.find_link(example)
        assert link == link_parser.Link(
            start=17,
            end=33,
            title="Sweden",
            raw_location="SE_flag",
            parsed_location=parse.urlparse("SE_flag"),
            alt_text="",
            is_reference=True,
        )


class TestReferences:
    def test__no_referenes(self):
        assert link_parser.Reference.parse('A totally normal line.', lineno=1) is None
        assert link_parser.Reference.parse('A line with [a link](/wiki/Link).', lineno=1) is None

    def test__references(self):
        assert link_parser.Reference.parse('[refname]: /wiki/Article', lineno=10) == link_parser.Reference(
            lineno=10,
            name='refname',
            raw_location='/wiki/Article', parsed_location=parse.urlparse('/wiki/Article'),
            alt_text='',
        )

        assert link_parser.Reference.parse('[ref]: /some/path "Alt text"', lineno=11) == link_parser.Reference(
            lineno=11,
            name='ref',
            raw_location='/some/path', parsed_location=parse.urlparse('/some/path'),
            alt_text='Alt text'
        )

        assert link_parser.Reference.parse(
            '[ref]: https://example.com/image.png "Image"', lineno=12
        ) == link_parser.Reference(
            lineno=12,
            name='ref',
            raw_location='https://example.com/image.png',
            parsed_location=parse.urlparse('https://example.com/image.png'),
            alt_text='Image'
        )


class TestReferenceFinder:
    def test__find_references(self):
        text = textwrap.dedent('''
            # An article

            [stray]: /refe/ren/ce
        ''').strip()

        expected_reference = link_parser.Reference(
            lineno=3, name='stray', raw_location='/refe/ren/ce',
            parsed_location=parse.urlparse('/refe/ren/ce'), alt_text=''
        )
        assert link_parser.find_references(text) == {'stray': expected_reference}

    def test__more_references(self):
        text = textwrap.dedent('''
            # Lorem ipsum

            Dolor [sit][sit_ref] amet.

            [sit_ref]: /a/random/insertion

            It is a long established fact that a ![reader][reader_ref] will be distracted by... [KEEP READING]

            [reader_ref]: img/reader.png "A reader"
        ''').strip()

        link_ref = link_parser.Reference(
            lineno=5, name='sit_ref', raw_location='/a/random/insertion',
            parsed_location=parse.urlparse('/a/random/insertion'), alt_text=''
        )
        image_ref = link_parser.Reference(
            lineno=9, name='reader_ref', raw_location='img/reader.png',
            parsed_location=parse.urlparse('img/reader.png'), alt_text='A reader'
        )

        assert link_parser.find_references(text) == {
            'sit_ref': link_ref,
            'reader_ref': image_ref
        }


class TestLinkObject:
    def test__resolution(self):
        link = link_parser.find_link('This is an [example][example_ref].')
        references = link_parser.find_references('[example_ref]: https://example.com "Example"')

        assert link.resolve(references) == references['example_ref']
        assert link.resolve({}) is None
