from tests.conftest import VisualTest, VisualTestCase

from wikitools_cli import osu_wiki_tools
from wikitools_cli.commands import check_links, check_outdated_articles, check_yaml

test = VisualTest(
    name="Print help",
    description="This should print help descriptions",
    cases=[
        VisualTestCase(
            description="osu_wiki_tools.main run with --help",
            function=lambda : osu_wiki_tools.main("--help")
        ),
        VisualTestCase(
            description="check_links.main run with --help",
            function=lambda : check_links.main("--help")
        ),
        VisualTestCase(
            description="check_outdated_articles.main run with --help",
            function=lambda : check_outdated_articles.main("--help")
        ),
        VisualTestCase(
            description="check_yaml.main run with --help",
            function=lambda : check_yaml.main("--help")
        ),
    ]
)
