from tests.conftest import VisualTest, VisualTestCase

from wikitools_cli.commands import check_links


test = VisualTest(
    name="Check links",
    description="This should print errors for erroneous links",
    cases=[
        VisualTestCase(
            name="malformed_link",
            description="Malformed link (1 error)",
            function=lambda : check_links.main("--root", "tests/test_articles", "--target", "wiki/malformed_link/en.md")
        ),
        VisualTestCase(
            name="not_found",
            description="Not found (3 errors)",
            function=lambda : check_links.main("--root", "tests/test_articles", "--target", "wiki/not_found/en.md")
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
            description="Missing identifier (1 error)",
            function=lambda : check_links.main("--root", "tests/test_articles",  "--target", "wiki/missing_identifier/en.md")
        ),
    ]
)
