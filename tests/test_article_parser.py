import itertools
import textwrap
from urllib import parse

import conftest

from wikitools import article_parser, link_parser, redirect_parser, errors as error_types


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

        article = article_parser.Article.parse_file('wiki/Article/en.md')

        assert article.directory == 'wiki/Article'
        assert article.filename == 'en.md'
        assert article.identifiers == ['list-of-references']
        assert article.references == {
            'links_ref': link_parser.Reference(
                lineno=9, name='links_ref', raw_location='https://example.com',
                parsed_location=parse.urlparse('https://example.com'), alt_text=''
            ),
            'vier_ref': link_parser.Reference(
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

        article = article_parser.Article.parse_file('wiki/Article/en.md')
        assert len(article.references) == 0  # commented references are also skipped

        links = sum((line.links for line in article.lines.values()), start=[])
        locations = set(_.raw_location for _ in links)
        assert locations == {'/wiki/Red', 'img/violet.png', 'blue_ref'}


class TestArticleChecker:
    def test__check_article__clean(self, root):
        conftest.create_files(
            root,
            (
                'Article/en.md',
                textwrap.dedent('''
                    # An article

                    It's a [very](Subarticle) [well](/wiki/Brticle) written ![line](img/line.png).

                    This line, however, uses a [redirect](/wiki/Old_link).
                ''').strip()
            ),
            ('Article/Subarticle/en.md', ''),
            ('Brticle/en.md', ''),
            ('Article/img/line.png', ''),
            ('redirect.yaml', '"old_link": "Article/Subarticle"')
        )

        redirects = redirect_parser.load_redirects(root.join('redirect.yaml'))
        article = article_parser.Article.parse_file('wiki/Article/en.md')
        assert article.check_links(redirects) == {}

    def test__check_article__bad(self, root):
        conftest.create_files(
            root,
            (
                'Article/en.md',
                textwrap.dedent('''
                    # An article

                    [Some](/wiki/Valid_link) of the lines contain valid links and images ![yep](img/yep.png).

                    ## Disaster

                    [What?](/wiki/Broken_link)

                    - No, really, [what is this](Bad_relative_link)?
                    - Did you even [check your links](/wiki/Broken_redirect)? [Are you sure?][sure_ref]
                    - **No formatting *[at all][at_all_ref]?!*
                    - Subpar ![a dismissive picture](img/you_tried.jpeg)

                    ## References

                    [sure_ref]: /wiki/Article
                ''').strip()
            ),
            ('Article/img/yep.png', ''),
            ('Valid_link/en.md', ''),
            ('redirect.yaml', '"broken_redirect": "Another_missing_article"')
        )

        redirects = redirect_parser.load_redirects(root.join('redirect.yaml'))
        article = article_parser.Article.parse_file('wiki/Article/en.md')
        results = article.check_links(redirects)

        flattened_results = []
        for lineno, rr in sorted(results.items()):
            for result in rr:
                flattened_results.append((lineno, result))

        assert len(flattened_results) == 5

        assert set(r.link.raw_location for (_, r) in flattened_results) == {
            '/wiki/Broken_link',
            'Bad_relative_link',
            '/wiki/Broken_redirect',
            'at_all_ref',
            'img/you_tried.jpeg'
        }

        broken_link_error = flattened_results[0][1].error
        broken_link = flattened_results[0][1].link
        assert isinstance(broken_link_error, error_types.LinkNotFound)
        assert broken_link_error.location == 'Broken_link'
        assert (flattened_results[0][0], broken_link.start) == (7, 0)

        broken_rel_link_error = flattened_results[1][1].error
        broken_rel_link = flattened_results[1][1].link
        assert isinstance(broken_rel_link_error, error_types.LinkNotFound)
        assert broken_rel_link_error.location == 'Article/Bad_relative_link'
        assert (flattened_results[1][0], broken_rel_link.start) == (9, 14)

        broken_redirect_error = flattened_results[2][1].error
        broken_redirect = flattened_results[2][1].link
        assert isinstance(broken_redirect_error, error_types.BrokenRedirect)
        assert broken_redirect_error.location == 'Broken_redirect'
        assert (flattened_results[2][0], broken_redirect.start) == (10, 15)

        broken_redirect_error = flattened_results[3][1].error
        broken_redirect_2 = flattened_results[3][1].link
        assert isinstance(broken_redirect_error, error_types.MissingReference)
        assert broken_redirect_error.location == 'at_all_ref'
        assert (flattened_results[3][0], broken_redirect_2.start) == (11, 19)

        broken_image_error = flattened_results[4][1].error
        broken_image = flattened_results[4][1].link
        assert isinstance(broken_image_error, error_types.LinkNotFound)
        assert broken_image_error.location == 'Article/img/you_tried.jpeg'
        assert (flattened_results[4][0], broken_image.start) == (12, 10)

        # all lines, even with references, were cached
        assert all(_[0] in article.lines for _ in flattened_results)
