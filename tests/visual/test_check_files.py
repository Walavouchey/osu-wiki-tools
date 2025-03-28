from tests.conftest import VisualTest, VisualTestCase

from wikitools_cli.commands import check_files


test = VisualTest(
    name="Check files",
    description="This should print errors regarding file and folder structure",
    cases=[
        VisualTestCase(
            name="missing_english_version",
            description="Missing English version (1 error)",
            function=lambda : check_files.main("--root", "tests/test_articles", "--all")
        ),
    ]
)
