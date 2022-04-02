import textwrap

import conftest
from wikitools import article_parser, link_checker, link_parser, redirect_parser, errors as error_types, reference_parser


def dummy_article(path):
    return article_parser.Article(path, lines=[], references=[], identifiers=[])


class TestArticleLinks:
    def test__valid_absolute_link(self, root):
        conftest.create_files(
            root,
            ('First_article/en.md', '# First article')
        )

        link = link_parser.find_link('Check the [first article](/wiki/First_article).')
        error = link_checker.check_link(
            article=dummy_article('does/not/matter'), link_=link, redirects={}, references={}, all_articles={}
        )
        assert error is None

    def test__invalid_absolute_link(self, root):
        conftest.create_files(
            root,
            ('Another_article/en.md', '# Another article')
        )

        for line in (
            'This link is [broken](/wiki/Another_article/Some_nonsense).',
            'This link is [broken](/wiki/A_random_directory), too.'
        ):
            link = link_parser.find_link(line)
            error = link_checker.check_link(
                article=dummy_article('does/not/matter'), link_=link, redirects={}, references={}, all_articles={}
            )
            assert isinstance(error, error_types.LinkNotFound)

    def test__valid_reference(self, root):
        conftest.create_files(
            root,
            ('My_article/en.md', '# My article')
        )

        link = link_parser.find_link('This link is [working][article_ref].')
        references = reference_parser.extract_all('[article_ref]: /wiki/My_article "Something something"')
        error = link_checker.check_link(
            article=dummy_article('does/not/matter'), link_=link, redirects={}, references=references, all_articles={}
        )
        assert error is None

    def test__invalid_reference(self, root):
        conftest.create_files(
            root,
            ('Obscure_article/en.md', '# First article')
        )

        link = link_parser.find_link('This link is [not working][article_ref].')
        references = reference_parser.extract_all('[other_ref]: /wiki/Obscure_article "Something something"')
        error = link_checker.check_link(
            article=dummy_article('does/not/matter'), link_=link, redirects={}, references=references, all_articles={}
        )
        assert isinstance(error, error_types.MissingReference)
        assert error.location == 'article_ref'

    def test__valid_relative_link(self, root):
        conftest.create_files(
            root,
            ('Batteries/en.md', '# Batteries'),
            ('Batteries/Included/en.md', '# Included'),
            ('Batteries/Included/And_even_more/en.md', '# And even more!')
        )

        for line in (
            '[Alkaline FTW](Included).',
            '[Alkaline FTW](./Included).',
            '[Alkaline FTW](../Batteries/Included).',  # I hope we will never see this, but let's be ready
            '[Alkaline FTW](Included/And_even_more).'
        ):
            link = link_parser.find_link(line)
            error = link_checker.check_link(
                article=dummy_article('wiki/Batteries/en.md'), link_=link, redirects={}, references={}, all_articles={}
            )
            assert error is None

    def test__invalid_relative_link(self, root):
        conftest.create_files(
            root,
            ('Existing_article/en.md', '# Existing article')
        )

        link = link_parser.find_link('This link [does not work](Broken_link).')
        error = link_checker.check_link(
            article=dummy_article('wiki/Existing_article/en.md'), link_=link, redirects={}, references={}, all_articles={}
        )
        assert isinstance(error, error_types.LinkNotFound)


class TestImageLinks:
    def test__valid_absolute_link(self, root):
        conftest.create_files(
            root,
            ('Article/en.md', '# Article'),
            ('img/battery.png', '')
        )

        link = link_parser.find_link('Check this ![out](/wiki/img/battery.png).')
        error = link_checker.check_link(
            article=dummy_article('does/not/matter'), link_=link, redirects={}, references={}, all_articles={}
        )
        assert error is None

    def test__invalid_absolute_link(self, root):
        conftest.create_files(
            root,
            ('New_article/en.md', '# New article'),
            ('img/battery.png', '')
        )

        link = link_parser.find_link('Do not check this ![out](/wiki/img/nonsense.png).')
        error = link_checker.check_link(
            article=dummy_article('does/not/matter'), link_=link, redirects={}, references={}, all_articles={}
        )
        assert isinstance(error, error_types.LinkNotFound)

    def test__valid_relative_link(self, root):
        conftest.create_files(
            root,
            ('Beatmap/en.md', '# Beatmap'),
            ('Beatmap/img/beatmap.png', '')
        )

        link = link_parser.find_link('Behold, the beatmap ![beatmap](img/beatmap.png "Wow!").')
        error = link_checker.check_link(
            article=dummy_article('wiki/Beatmap/en.md'), link_=link, redirects={}, references={}, all_articles={}
        )
        assert error is None

    def test__invalid_relative_link(self, root):
        conftest.create_files(
            root,
            ('Difficulty/en.md', '# Difficulty'),
            ('Difficulty/img/difficulty.png', '')
        )

        link = link_parser.find_link('Nothing to see here ![please](img/none.png "disperse").')
        error = link_checker.check_link(
            article=dummy_article('wiki/Difficulty/en.md'), link_=link, redirects={}, references={}, all_articles={}
        )
        assert isinstance(error, error_types.LinkNotFound)


class TestRedirectedLinks:
    def test__valid_link(self, root):
        conftest.create_files(
            root,
            ('redirect.yaml', '"old_link": "New_article"'),
            ('New_article/en.md', '# New article'),
        )

        redirects = redirect_parser.load_redirects(root.join('redirect.yaml'))
        link = link_parser.find_link('Please read the [old article](/wiki/Old_LiNK).')
        error = link_checker.check_link(
            article=dummy_article('does/not/matter'), link_=link, redirects=redirects, references={}, all_articles={}
        )
        assert error is None

    def test__invalid_link(self, root):
        conftest.create_files(
            root,
            (
                'redirect.yaml', textwrap.dedent('''
                    # junk comment to fill the lines
                    "old_link": "Wrong_redirect"
                ''').strip()
            ),
            ('New_article/en.md', '# New article'),
        )

        redirects = redirect_parser.load_redirects(root.join('redirect.yaml'))
        link = link_parser.find_link('Please read the [old article](/wiki/Old_link).')
        error = link_checker.check_link(
            article=dummy_article('does/not/matter'), link_=link, redirects=redirects, references={}, all_articles={}
        )
        assert isinstance(error, error_types.BrokenRedirect)
        assert error.redirect_lineno == 2
        assert error.location == 'Old_link'
        assert error.redirect_destination == 'Wrong_redirect'


class TestExternalLinks:
    def test__all_external_links__valid(self):
        for line in (
            'Check the [example](https://example.com "Example").',
            'Contact [accounts@example.com](mailto:accounts@example.com).',
            'Look, [the web chat](irc://cho.ppy.sh)!',
            'I am [not even trying](htttttttttttttttttps://example.com).',
        ):
            link = link_parser.find_link(line)
            error = link_checker.check_link(
                article=dummy_article('does/not/matter'), link_=link, redirects={}, references={}, all_articles={}
            )
            assert error is None


class TestSectionLinks:
    def test__valid_absolute_link(self, root):
        conftest.create_files(
            root,
            (
                'New_article/en.md',
                textwrap.dedent('''
                    # New article

                    ## Some real heading

                    Some real though from a real person.
                ''').strip()
            )
        )
        new_article = article_parser.parse('wiki/New_article/en.md')
        assert new_article.identifiers == ['some-real-heading']
        all_articles = {new_article.path: new_article}

        link = link_parser.find_link('Please read the [article](/wiki/New_article#some-real-heading).')
        error = link_checker.check_link(
            article=dummy_article('does/not/matter'), link_=link, redirects={}, references={}, all_articles=all_articles
        )
        assert error is None

    def test__valid_absolute_link__translation(self, root):
        conftest.create_files(
            root,
            ('New_article/en.md', '# New article'),
            (
                'New_article/ru.md',
                textwrap.dedent('''
                    # New article

                    ## Заголовок (translated)
                ''')
            )
        )

        all_articles = {
            path: article_parser.parse(path)
            for path in ('wiki/New_article/en.md', 'wiki/New_article/ru.md')
        }

        link = link_parser.find_link('См. [другую статью](/wiki/New_article#заголовок-(translated)).')
        error = link_checker.check_link(
            article=dummy_article('wiki/Some_other_article/ru.md'), link_=link, redirects={}, references={}, all_articles=all_articles
        )
        assert error is None

    def test__invalid_absolute_link__missing_heading(self, root):
        conftest.create_files(
            root,
            ('New_article/en.md', '# New article'),
        )
        new_article = dummy_article('wiki/New_article/en.md')
        all_articles = {new_article.path: new_article}

        link = link_parser.find_link('Please read the [article](/wiki/New_article#some-nonexistent-heading).')
        error = link_checker.check_link(
            article=dummy_article('does/not/matter'), link_=link, redirects={}, references={}, all_articles=all_articles
        )
        assert isinstance(error, error_types.MissingIdentifier)
        assert error.identifier == 'some-nonexistent-heading'
        assert error.path == 'wiki/New_article/en.md'
        assert not error.translation_available

    def test__invalid_absolute_link__missing_translation(self, root):
        conftest.create_files(
            root,
            (
                'New_article/en.md',
                textwrap.dedent('''
                    # New article

                    ## Self-check

                    This line exists.
                ''').strip()
            )
        )
        new_article = article_parser.parse('wiki/New_article/en.md')
        all_articles = {new_article.path: new_article}

        # pretend we're linking from a French page
        link = link_parser.find_link("Merci de lire l'[article](/wiki/New_article#auto-contrôle).")
        error = link_checker.check_link(
            article=dummy_article('wiki/Some_other_article/fr.md'), link_=link, redirects={}, references={}, all_articles=all_articles
        )
        assert isinstance(error, error_types.MissingIdentifier)
        assert error.identifier == 'auto-contrôle'
        assert error.path == 'wiki/New_article/en.md'

    def test__valid_relative_link(self, root):
        conftest.create_files(
            root,
            ('New_article/en.md', '# New article'),
            (
                'New_article/Included_article/en.md',
                textwrap.dedent('''
                    # Included article

                    ## Subheading

                    This line exists.
                ''').strip()
            )
        )
        all_articles = {
            path: article_parser.parse(path)
            for path in ('wiki/New_article/en.md', 'wiki/New_article/Included_article/en.md')
        }

        link = link_parser.find_link("Please follow the [included article](Included_article#subheading).")
        error = link_checker.check_link(
            article=dummy_article('wiki/New_article/en.md'), link_=link, redirects={}, references={}, all_articles=all_articles
        )
        assert error is None

    def test__invalid_relative_link(self, root):
        conftest.create_files(
            root,
            ('New_article/en.md', '# New article'),
            (
                'New_article/Included_article/en.md',
                textwrap.dedent('''
                    # Included article

                    ## Subheading

                    This line exists.
                ''').strip()
            )
        )
        all_articles = {
            path: article_parser.parse(path)
            for path in ('wiki/New_article/en.md', 'wiki/New_article/Included_article/en.md')
        }

        link = link_parser.find_link("Please follow the [included article](Included_article#wrong-subheading).")
        error = link_checker.check_link(
            article=dummy_article('wiki/New_article/en.md'), link_=link, redirects={}, references={}, all_articles=all_articles
        )
        assert isinstance(error, error_types.MissingIdentifier)
        assert error.identifier == 'wrong-subheading'
        assert error.path == 'wiki/New_article/Included_article/en.md'

    def test__valid_redirect(self, root):
        conftest.create_files(
            root,
            ('redirect.yaml', '"old_location": "Target_article"'),
            ('New_article/en.md', '# New article'),
            (
                'Target_article/en.md',
                textwrap.dedent('''
                    # Included article

                    ## Subheading

                    This line exists.
                ''').strip()
            )
        )
        all_articles = {
            path: article_parser.parse(path)
            for path in ('wiki/New_article/en.md', 'wiki/Target_article/en.md')
        }
        redirects = redirect_parser.load_redirects(root.join('redirect.yaml'))

        link = link_parser.find_link("Please follow the [target article](/wiki/Old_location#subheading).")
        error = link_checker.check_link(
            article=dummy_article('wiki/New_article/en.md'), link_=link, redirects=redirects, references={}, all_articles=all_articles
        )
        assert error is None

    def test__invalid_redirect(self, root):
        conftest.create_files(
            root,
            ('redirect.yaml', '"old_location": "Target_article"'),
            ('New_article/en.md', '# New article'),
            (
                'Target_article/en.md',
                textwrap.dedent('''
                    # Included article

                    ## Subheading

                    This line exists.
                ''').strip()
            )
        )
        all_articles = {
            path: article_parser.parse(path)
            for path in ('wiki/New_article/en.md', 'wiki/Target_article/en.md')
        }
        redirects = redirect_parser.load_redirects(root.join('redirect.yaml'))

        link = link_parser.find_link("Please follow the [target article](/wiki/Old_location#totally-wrong-heading).")
        error = link_checker.check_link(
            article=dummy_article('wiki/New_article/en.md'), link_=link, redirects=redirects, references={}, all_articles=all_articles
        )
        assert isinstance(error, error_types.MissingIdentifier)
        assert error.identifier == 'totally-wrong-heading'
        assert error.path == 'wiki/Target_article/en.md'


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
        article = article_parser.parse('wiki/Article/en.md')
        assert link_checker.check_article(article, redirects, all_articles={}) == {}

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
        article = article_parser.parse('wiki/Article/en.md')
        results = link_checker.check_article(article, redirects, all_articles={})

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
