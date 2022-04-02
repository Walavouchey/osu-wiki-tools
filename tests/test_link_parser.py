import os
import textwrap
from urllib import parse

import pytest
import conftest

from wikitools import link_parser, errors, redirect_parser, reference_parser


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


class TestLinkObject:
    def test__resolution(self):
        link = link_parser.find_link('This is an [example][example_ref].')
        references = reference_parser.extract_all('[example_ref]: https://example.com "Example"')

        assert link.resolve(references) == references['example_ref']
        assert link.resolve({}) is None


class TestArticleLinks:
    def test__valid_absolute_link(self, root):
        conftest.create_files(
            root,
            ('First_article/en.md', '# First article')
        )

        link = link_parser.find_link('Check the [first article](/wiki/First_article).')
        error = link_parser.check_link(redirects={}, references={}, current_article_dir='does/not/matter', link_=link)
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
            error = link_parser.check_link(redirects={}, references={}, current_article_dir='does/not/matter', link_=link)
            assert isinstance(error, errors.LinkNotFound)

    def test__valid_reference(self, root):
        conftest.create_files(
            root,
            ('My_article/en.md', '# My article')
        )

        link = link_parser.find_link('This link is [working][article_ref].')
        references = reference_parser.extract_all('[article_ref]: /wiki/My_article "Something something"')
        error = link_parser.check_link(redirects={}, references=references, current_article_dir='does/not/matter', link_=link)
        assert error is None

    def test__invalid_reference(self, root):
        conftest.create_files(
            root,
            ('Obscure_article/en.md', '# First article')
        )

        link = link_parser.find_link('This link is [not working][article_ref].')
        references = reference_parser.extract_all('[other_ref]: /wiki/Obscure_article "Something something"')
        error = link_parser.check_link(redirects={}, references=references, current_article_dir='does/not/matter', link_=link)
        assert isinstance(error, errors.MissingReference)
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
            error = link_parser.check_link(redirects={}, references={}, current_article_dir='Batteries', link_=link)
            assert error is None

    def test__invalid_relative_link(self, root):
        conftest.create_files(
            root,
            ('Existing_article/en.md', '# Existing article')
        )

        link = link_parser.find_link('This link [does not work](Broken_link).')
        error = link_parser.check_link(redirects={}, references={}, current_article_dir='Existing_article', link_=link)
        assert isinstance(error, errors.LinkNotFound)


class TestImageLinks:
    def test__valid_absolute_link(self, root):
        conftest.create_files(
            root,
            ('Article/en.md', '# Article'),
            ('img/battery.png', '')
        )

        link = link_parser.find_link('Check this ![out](/wiki/img/battery.png).')
        error = link_parser.check_link(redirects={}, references={}, current_article_dir='does/not/matter', link_=link)
        assert error is None

    def test__invalid_absolute_link(self, root):
        conftest.create_files(
            root,
            ('New_article/en.md', '# New article'),
            ('img/battery.png', '')
        )

        link = link_parser.find_link('Do not check this ![out](/wiki/img/nonsense.png).')
        error = link_parser.check_link(redirects={}, references={}, current_article_dir='does/not/matter', link_=link)
        assert isinstance(error, errors.LinkNotFound)

    def test__valid_relative_link(self, root):
        conftest.create_files(
            root,
            ('Beatmap/en.md', '# Beatmap'),
            ('Beatmap/img/beatmap.png', '')
        )

        link = link_parser.find_link('Behold, the beatmap ![beatmap](img/beatmap.png "Wow!").')
        error = link_parser.check_link(redirects={}, references={}, current_article_dir='Beatmap', link_=link)
        assert error is None

    def test__invalid_relative_link(self, root):
        conftest.create_files(
            root,
            ('Difficulty/en.md', '# Difficulty'),
            ('Difficulty/img/difficulty.png', '')
        )

        link = link_parser.find_link('Nothing to see here ![please](img/none.png "disperse").')
        error = link_parser.check_link(redirects={}, references={}, current_article_dir='Difficulty', link_=link)
        assert isinstance(error, errors.LinkNotFound)


class TestRedirectedLinks:
    def test__valid_link(self, root):
        conftest.create_files(
            root,
            ('redirect.yaml', '"old_link": "New_article"'),
            ('New_article/en.md', '# New article'),
        )

        redirects = redirect_parser.load_redirects(root.join('redirect.yaml'))
        link = link_parser.find_link('Please read the [old article](/wiki/Old_LiNK).')
        error = link_parser.check_link(redirects=redirects, references={}, current_article_dir='does/not/matter', link_=link)
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
        error = link_parser.check_link(redirects=redirects, references={}, current_article_dir='does/not/matter', link_=link)
        assert isinstance(error, errors.BrokenRedirect)
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
            error = link_parser.check_link(redirects={}, references={}, current_article_dir='does/not/matter', link_=link)
            assert error is None


class TestSectionLinks:
    @pytest.mark.skip("not implemented yet")
    def test__valid_absolute_link(self):
        raise NotImplementedError()

    @pytest.mark.xfail(reason="sections are not accounted for")
    def test__invalid_absolute_link__missing_heading(self, root):
        conftest.create_files(
            root,
            ('New_article/en.md', '# New article'),
        )

        link = link_parser.find_link('Please read the [article](/wiki/New_article#some-nonexistent-heading).')
        error = link_parser.check_link(redirects={}, references={}, current_article_dir='does/not/matter', link_=link)
        assert isinstance(error, errors.MissingIdentifier)
        assert error.identifier == 'some-nonexistent-heading'
        assert error.path == 'wiki/New_article/en.md'

    @pytest.mark.skip("not implemented yet")
    def test__invalid_absolute_link__missing_translation(self):
        raise NotImplementedError()

    @pytest.mark.skip("not implemented yet")
    def test__valid_relative_link(self):
        raise NotImplementedError()

    @pytest.mark.skip("not implemented yet")
    def test__invalid_relative_link(self):
        raise NotImplementedError()

    @pytest.mark.skip("not implemented yet")
    def test__valid_redirect(self):
        raise NotImplementedError()

    @pytest.mark.skip("not implemented yet")
    def test__invalid_redirect(self):
        raise NotImplementedError()