from tests.conftest import VisualTest, VisualTestCase
from tests.conftest import DummyRepository
import tests.utils as utils

from wikitools_cli.commands import check_outdated_articles as outdater


def check_outdated_articles_test():
    with DummyRepository() as root:
        article_paths = [
            'wiki/Article/en.md',
            'wiki/Article/fr.md',
            'wiki/Article/fil.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
        ]

        utils.create_files(root, *((path, '# Article') for path in article_paths))
        utils.stage_all_and_commit("add articles")

        utils.create_files(root, *(
            (article_path, '# Article\n\nThis is an article in English.') for article_path in
            utils.take(article_paths, "en.md")
        ))
        utils.stage_all_and_commit("modify english article")
        commit_hash = utils.get_last_commit_hash()

        outdater.main("--base-commit", "HEAD^", "--outdated-since", commit_hash)


def check_outdated_articles_test_no_recommend_autofix():
    with DummyRepository() as root:
        article_paths = [
            'wiki/Article/en.md',
            'wiki/Article/fr.md',
            'wiki/Article/fil.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
        ]

        utils.create_files(root, *((path, '# Article') for path in article_paths))
        utils.stage_all_and_commit("add articles")

        utils.create_files(root, *(
            (article_path, '# Article\n\nThis is an article in English.') for article_path in
            utils.take(article_paths, "en.md")
        ))
        utils.stage_all_and_commit("modify english article")
        commit_hash = utils.get_last_commit_hash()

        outdater.main("--no-recommend-autofix", "--base-commit", "HEAD^", "--outdated-since", commit_hash)


test = VisualTest(
    name="Check outdated articles",
    description="This should complain about translations not being outdated properly",
    cases=[
        VisualTestCase(
            name="non_outdated_articles",
            description="Non-outdated articles (4 errors)",
            function=check_outdated_articles_test
        ),
        VisualTestCase(
            name="non_outdated_articles",
            description="Non-outdated articles with --no-recommend-autofix (4 errors)",
            function=check_outdated_articles_test_no_recommend_autofix
        )
    ]
)
