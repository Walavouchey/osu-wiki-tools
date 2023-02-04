import collections
import textwrap
from urllib import parse

import tests.conftest
import tests.utils as utils

from wikitools import article_parser, reference_parser


class TestArticleParser:
    def test__read_article(self, root):
        utils.create_files(
            root,
            (
                'wiki/Article/en.md',
                textwrap.dedent('''
                    ---
                    stub: true
                    tags:
                      - k1
                      - m1
                    ---

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
        assert article.path == 'wiki/Article/en.md'
        assert article.identifiers == {'list-of-references': 18}
        assert article.references == {
            'links_ref': reference_parser.Reference(
                lineno=16, name='links_ref', raw_location='https://example.com',
                parsed_location=parse.urlparse('https://example.com'), title=''
            ),
            'vier_ref': reference_parser.Reference(
                lineno=20, name='vier_ref', raw_location='/wiki/Article_three',
                parsed_location=parse.urlparse('/wiki/Article_three'), title='Links!'
            )
        }
        assert article.front_matter["stub"] is True
        assert article.front_matter["tags"] == ["k1", "m1"]

        assert set(article.lines.keys()) == {10, 12, 14}
        # lines are stored as-is, with trailing line breaks
        assert article.lines[10].raw_line == 'Links! [Links](https://example.com)!\n'

    def test__read_newspost(self, root):
        utils.create_files(
            root,
            (
                'news/newspost.md',
                textwrap.dedent('''
                    ---
                    layout: post
                    title: News!!!
                    date: 2021-10-21 15:00:00 +0000
                    ---

                    Links! [Links](https://example.com)!

                    Links, [zwo](/wiki/Article_two), [drei](Nested_article), [vier][vier_ref]!

                    [Links][links_ref]!

                    [links_ref]: https://example.com

                    ## List of references

                    [vier_ref]: /wiki/Article_three "Links!"
                ''').strip()
            )
        )

        article = article_parser.parse('news/newspost.md')

        assert article.directory == 'news'
        assert article.filename == 'newspost.md'
        assert article.path == 'news/newspost.md'
        assert article.identifiers == {'list-of-references': 15}
        assert article.references == {
            'links_ref': reference_parser.Reference(
                lineno=13, name='links_ref', raw_location='https://example.com',
                parsed_location=parse.urlparse('https://example.com'), title=''
            ),
            'vier_ref': reference_parser.Reference(
                lineno=17, name='vier_ref', raw_location='/wiki/Article_three',
                parsed_location=parse.urlparse('/wiki/Article_three'), title='Links!'
            )
        }
        assert article.front_matter["layout"] == "post"
        assert article.front_matter["title"] == "News!!!"
        assert article.front_matter["date"] == "2021-10-21 15:00:00 +0000"

        assert set(article.lines.keys()) == {7, 9, 11}
        # lines are stored as-is, with trailing line breaks
        assert article.lines[7].raw_line == 'Links! [Links](https://example.com)!\n'

    def test__read_article__with_comments(self, root):
        utils.create_files(
            root,
            (
                'wiki/Article/en.md',
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
                    A wild {id=identifier}
                    -->

                    <!-- Another wild {#identifier} -->
                ''').strip()
            )
        )

        article = article_parser.parse('wiki/Article/en.md')
        assert len(article.references) == 0  # commented references are also skipped
        assert not article.front_matter

        links = sum((line.links for line in article.lines.values()), start=[])
        locations = set(_.raw_location for _ in links)
        assert locations == {'/wiki/Red', 'img/violet.png', 'blue_ref'}
        assert article.identifiers == {}

    def test__repeating_headings(self, root):
        utils.create_files(
            root,
            (
                'wiki/Ranking_criteria/en.md',
                textwrap.dedent('''
                    # Ranking criteria

                    ## Section

                    ## Section

                    ## Something else

                    ## Random
                    
                    <!-- A {#random} comment -->

                    ## Tricky section {#random}

                    ## Section
                ''').strip()
            )
        )

        article = article_parser.parse('wiki/Ranking_criteria/en.md')
        assert article.identifiers == {
            'section': 3,
            'section.1': 5,
            'something-else': 7,
            'random': 9,
            'random.1': 13,
            'section.2': 15,
        }

    def test__ignore_comments(self, root):
        utils.create_files(
            root,
            (
                'wiki/Comments/en.md',
                textwrap.dedent('''
                    # Comments

                    <!-- Don't mention [comments](/wiki/HTML#comment). -->

                    <!-- Don't mention the [comments](/wiki/HTML#comment) at all.
                        Yes, even if they span across several [lines](/wiki/Power_line).
                        Please be [silent](/wiki/Silence) about that, okay? --> [Test](/wiki/Test)

                    There is [no](/wiki/No) support<!-- for the [comments](/wiki/HTML#comment) --> on the wiki.
                ''').strip()
            )
        )
        article = article_parser.parse('wiki/Comments/en.md')
        assert set(article.lines.keys()) == {7, 9}

        assert len(article.lines[7].links) == 1
        assert article.lines[7].links[0].raw_location == "/wiki/Test"

        assert len(article.lines[9].links) == 1
        assert article.lines[9].links[0].raw_location == "/wiki/No"

    def test__ignore_code_blocks(self, root):
        utils.create_files(
            root,
            (
                'wiki/Code_blocks/en.md',
                textwrap.dedent('''
                    # Code blocks

                    ## Examples

                    `[Inline](/wiki/Inline)` | `[b][i]Inline[/i][/b]`

                    `` `[Also inline](/wiki/Also_inline)` ``

                    Let's take a [break](/wiki/Gameplay/Break)!

                    ``Some`` [fun stuff](/wiki/Fun_stuff) ``here``.

                    ```
                    [Multiline](/wiki/Multiline)
                    [b][i]No[/i][/b]
                    ```

                    ```markdown
                    [Multiline with syntax highlighting](/wiki/Multiline#syntax-highlighting)
                    [wow][wow_ref]

                    [wow_ref]: /wiki/Wow
                    ```
                ''').strip()
            )
        )
        article = article_parser.parse('wiki/Code_blocks/en.md')
        assert set(article.lines.keys()) == {9, 11}

        assert len(article.lines[9].links) == 1
        assert article.lines[9].links[0].raw_location == "/wiki/Gameplay/Break"

        assert len(article.lines[11].links) == 1
        assert article.lines[11].links[0].raw_location == "/wiki/Fun_stuff"


class TestFrontMatter:
    def test__read_write_to_existing_front_matter(self, root):
        cases = ["", "<!-- a comment -->\n\n", "<div> some html </div>\n\n"]
        for test_case in cases:
            article_path = root.join("en.md")
            article_path.write_text(textwrap.dedent('''
                ---
                tags:
                  - a
                  - aaa
                  - юниcode
                outdated: true
                ---

                {}# Test

                Lorem (ipsum).
            ''').format(test_case).strip(), encoding='utf-8')

            with article_path.open("r", encoding='utf-8') as fd:
                fm = article_parser.load_front_matter(fd)

            assert collections.OrderedDict(fm) == collections.OrderedDict({
                'tags': ['a', 'aaa', 'юниcode'],
                'outdated': True,
            })

            fm['outdated_since'] = '0000b4dc0ffee000'
            article_parser.save_front_matter(str(article_path), fm)

            new_contents = article_path.read_text(encoding='utf-8')
            assert new_contents == textwrap.dedent('''
                ---
                tags:
                  - a
                  - aaa
                  - юниcode
                outdated: true
                outdated_since: 0000b4dc0ffee000
                ---

                {}# Test

                Lorem (ipsum).
            ''').format(test_case).strip()

    def test__read_write_to_no_existing_front_matter(self, root):
        cases = ["", "<!-- a comment -->\n\n", "<div> some html </div>\n\n"]
        for test_case in cases:
            article_path = root.join("en.md")
            article_path.write_text(textwrap.dedent('''
                {}# Test

                Lorem (ipsum).
            ''').format(test_case).strip(), encoding='utf-8')

            with open(article_path, "r", encoding='utf-8') as fd:
                front_matter = article_parser.load_front_matter(fd)
            front_matter['tags'] = ['a', 'aaa', 'юниcode']
            front_matter['outdated'] = True
            article_parser.save_front_matter(article_path, front_matter)

            with article_path.open("r", encoding='utf-8') as fd:
                print("Article contents:\n" + fd.read())
                fd.seek(0)
                fm = article_parser.load_front_matter(fd)

            assert collections.OrderedDict(fm) == collections.OrderedDict({
                'tags': ['a', 'aaa', 'юниcode'],
                'outdated': True,
            })

            fm['outdated_since'] = '0000b4dc0ffee000'
            article_parser.save_front_matter(str(article_path), fm)

            new_contents = article_path.read_text(encoding='utf-8')
            assert new_contents == textwrap.dedent('''
                ---
                tags:
                  - a
                  - aaa
                  - юниcode
                outdated: true
                outdated_since: 0000b4dc0ffee000
                ---

                {}# Test

                Lorem (ipsum).
            ''').format(test_case).strip()
