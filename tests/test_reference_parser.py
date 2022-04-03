import textwrap
from urllib import parse

from wikitools import reference_parser


class TestReferences:
    def test__no_referenes(self):
        assert reference_parser.extract('A totally normal line.', lineno=1) is None
        assert reference_parser.extract('A line with [a link](/wiki/Link).', lineno=1) is None

    def test__references(self):
        assert reference_parser.extract('[refname]: /wiki/Article', lineno=10) == reference_parser.Reference(
            lineno=10,
            name='refname',
            raw_location='/wiki/Article', parsed_location=parse.urlparse('/wiki/Article'),
            alt_text='',
        )

        assert reference_parser.extract('[ref]: /some/path "Alt text"', lineno=11) == reference_parser.Reference(
            lineno=11,
            name='ref',
            raw_location='/some/path', parsed_location=parse.urlparse('/some/path'),
            alt_text='Alt text'
        )

        assert reference_parser.extract(
            '[ref]: https://example.com/image.png "Image"', lineno=12
        ) == reference_parser.Reference(
            lineno=12,
            name='ref',
            raw_location='https://example.com/image.png',
            parsed_location=parse.urlparse('https://example.com/image.png'),
            alt_text='Image'
        )


class TestReferenceFinder:
    def test__extract_all(self):
        text = textwrap.dedent('''
            # An article

            [stray]: /refe/ren/ce
        ''').strip()

        expected_reference = reference_parser.Reference(
            lineno=3, name='stray', raw_location='/refe/ren/ce',
            parsed_location=parse.urlparse('/refe/ren/ce'), alt_text=''
        )
        assert reference_parser.extract_all(text) == {'stray': expected_reference}

    def test__more_references(self):
        text = textwrap.dedent('''
            # Lorem ipsum

            Dolor [sit][sit_ref] amet.

            [sit_ref]: /a/random/insertion

            It is a long established fact that a ![reader][reader_ref] will be distracted by... [KEEP READING]

            [reader_ref]: img/reader.png "A reader"
        ''').strip()

        link_ref = reference_parser.Reference(
            lineno=5, name='sit_ref', raw_location='/a/random/insertion',
            parsed_location=parse.urlparse('/a/random/insertion'), alt_text=''
        )
        image_ref = reference_parser.Reference(
            lineno=9, name='reader_ref', raw_location='img/reader.png',
            parsed_location=parse.urlparse('img/reader.png'), alt_text='A reader'
        )

        assert reference_parser.extract_all(text) == {
            'sit_ref': link_ref,
            'reader_ref': image_ref
        }
