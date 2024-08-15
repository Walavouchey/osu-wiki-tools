from tests.conftest import VisualTest, VisualTestCase

from wikitools_cli.commands import check_links


test = VisualTest(
    name="Check links",
    description="This should print errors for erroneous links",
    cases=[
        VisualTestCase(
            name="malformed_link",
            description="Malformed link (2 errors)",
            function=lambda : check_links.main("--root", "tests/test_articles", "--target", "wiki/malformed_link/en.md")
        ),
        VisualTestCase(
            name="not_found_case_insensitive",
            description="Not found, case-insensitive (4 errors)",
            function=lambda : check_links.main("--root", "tests/test_articles", "--target", "wiki/not_found/en.md")
        ),
        VisualTestCase(
            name="not_found_case_sensitive",
            description="Not found, case-sensitive (5 errors)",
            function=lambda : check_links.main("--root", "tests/test_articles", "--target", "wiki/not_found/en.md", "--case-sensitive")
        ),
        VisualTestCase(
            name="broken_redirect",
            description="Broken redirect (1 error)",
            function=lambda : check_links.main("--root", "tests/test_articles", "--target", "wiki/broken_redirect/en.md")
        ),
        VisualTestCase(
            name="missing_reference",
            description="Missing reference (1 error)",
            function=lambda : check_links.main("--root", "tests/test_articles", "--target", "wiki/missing_reference/en.md")
        ),
        VisualTestCase(
            name="missing_identifier",
            description="Missing identifier (3 errors)",
            function=lambda : check_links.main("--root", "tests/test_articles",  "--target", "wiki/missing_identifier/en.md", "news/2023/news-post-bad-section-link.md")
        ),
        VisualTestCase(
            name="redirected_section_links",
            description="Redirected section links (2 errors)",
            function=lambda : check_links.main("--root", "tests/test_articles",  "--target", "wiki/redirected_sections/en.md")
        ),
    ]
)
