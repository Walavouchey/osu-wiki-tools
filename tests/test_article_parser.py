import textwrap
from urllib import parse

import conftest

from wikitools import article_parser, reference_parser


class TestArticleParser:
    def test__read_article(self, root):
        conftest.create_files(
            root,
            (
                'Article/en.md',
                textwrap.dedent('''
                    # An article

                    Links! [Links](https://example.com)!

                    Links, [zwo](/wiki/Article_two), [drei](Nested_article), [vier][vier_ref]!

                    [Links][links_ref]!

                    [links_ref]: https://example.com

                    ## List of references

                    [vier_ref]: /wiki/Article_three "Links!"
                ''').strip()
            )
        )

        article = article_parser.parse('wiki/Article/en.md')

        assert article.directory == 'wiki/Article'
        assert article.filename == 'en.md'
        assert article.identifiers == ['list-of-references']
        assert article.references == {
            'links_ref': reference_parser.Reference(
                lineno=9, name='links_ref', raw_location='https://example.com',
                parsed_location=parse.urlparse('https://example.com'), alt_text=''
            ),
            'vier_ref': reference_parser.Reference(
                lineno=13, name='vier_ref', raw_location='/wiki/Article_three',
                parsed_location=parse.urlparse('/wiki/Article_three'), alt_text='Links!'
            )
        }

        assert set(article.lines.keys()) == {3, 5, 7, 9, 13}
        # lines are stored as-is, with trailing line breaks
        assert article.lines[3].raw_line == 'Links! [Links](https://example.com)!\n'

    def test__read_article__with_comments(self, root):
        conftest.create_files(
            root,
            (
                'Article/en.md',
                textwrap.dedent('''
                    # An article

                    <!-- rewrite this? do we even need it?
                        Hear the poetry:
                    -->

                    Roses are [red](/wiki/Red),
                    Violets are [blue][blue_ref] ![](img/violet.png),
                    I've written a program
                    <!-- Which didn't have [a clue](/wiki/Clue) -->
                    But neither should you.

                    <!--
                    Multiline [comments](/wiki/Comment)?
                    In my [test](/wiki/Not_a_test)?

                    [blue_ref]: /wiki/Blue
                    -->
                ''').strip()
            )
        )

        article = article_parser.parse('wiki/Article/en.md')
        assert len(article.references) == 0  # commented references are also skipped

        links = sum((line.links for line in article.lines.values()), start=[])
        locations = set(_.raw_location for _ in links)
        assert locations == {'/wiki/Red', 'img/violet.png', 'blue_ref'}
