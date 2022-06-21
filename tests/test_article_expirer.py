import collections
import textwrap

import conftest

from wikitools import article_parser, git_utils

from wikitools_cli import check_expired_articles as expirer


def stage_all_and_commit(commit_message):
    git_utils.git("add", ".")
    git_utils.git("commit", "-m", commit_message)


class TestArticleExpirer:
    def test__list_all_translations(self, root):
        article_paths = [
            'Article/en.md',
            'Article/fr.md',
            'Article/pt-br.md',
            'Article/zh-tw.md',
            'Article/TRANSLATING.md',
            'Article/TEMPLATE.md',
        ]
        article_paths_with_root = ["wiki/" + path for path in article_paths]

        conftest.create_files(root, *((path, '# Article') for path in article_paths))

        assert list(expirer.list_translations(["wiki/Article"])) == article_paths_with_root[1:4]

    def test__list_modified_translations(self, root):
        git_utils.git("init")
        article_paths = [
            'Article/en.md',
            'Article/fr.md',
            'Article/pt-br.md',
            'Article/zh-tw.md',
            'Category1/Article/en.md',
            'Category1/Article/fr.md',
            'Category1/Article/pt-br.md',
            'Category1/Article/zh-tw.md',
            'Category1/Category2/Article/en.md',
            'Category1/Category2/Article/fr.md',
            'Category1/Category2/Article/pt-br.md',
            'Category1/Category2/Article/zh-tw.md',
            'Category1/Category2/Category3/Article/en.md',
            'Category1/Category2/Category3/Article/fr.md',
            'Category1/Category2/Category3/Article/pt-br.md',
            'Category1/Category2/Category3/Article/zh-tw.md',
        ]
        article_paths_with_root = ["wiki/" + path for path in article_paths]

        conftest.create_files(root, *((path, '') for path in article_paths))
        stage_all_and_commit("initial commit")

        conftest.create_files(root, *((path, '# Article') for path in article_paths))
        stage_all_and_commit("add article title")
        # note that at least two existing commits are necessary to get a diff using `revision^`
        commit_hash = git_utils.git("show", "HEAD", "--pretty=format:%H", "-s")

        modified_translations = expirer.list_modified_translations(commit_hash)
        assert modified_translations == set(filter(lambda x : "en.md" not in x, article_paths_with_root))

        conftest.create_files(root,
            *((path, '# Article\n\nCeci est un article en français.') for path in
            list(filter(lambda x : "fr.md" in x, article_paths)))
        )
        stage_all_and_commit("add article content")
        commit_hash = git_utils.git("show", "HEAD", "--pretty=format:%H", "-s")

        modified_translations = expirer.list_modified_translations(commit_hash)
        assert modified_translations == set(filter(lambda x : "fr.md" in x, article_paths_with_root))

    def test__list_modified_originals(self, root):
        git_utils.git("init")
        article_paths = [
            'Article/en.md',
            'Article2/en.md',
            'Article/fr.md',
            'Article2/fr.md',
            'Article/pt-br.md',
            'Article2/pt-br.md',
            'Article/zh-tw.md',
            'Article2/zh-tw.md',
        ]
        article_paths_with_root = ["wiki/" + path for path in article_paths]

        conftest.create_files(root, *((path, '# Article') for path in article_paths))
        stage_all_and_commit("add some articles")
        commit_hash = git_utils.git("show", "HEAD", "--pretty=format:%H", "-s")

        conftest.create_files(root, *zip(article_paths[0:2], [
            '# Article\n\nThis is an article in English.',
            '# Article\n\nThis is another article in English.',
        ]))
        stage_all_and_commit("add article content")
        commit_hash = git_utils.git("show", "HEAD", "--pretty=format:%H", "-s")

        modified_originals = expirer.list_modified_originals(commit_hash)
        assert modified_originals == article_paths_with_root[0:2]

    def test__validate_hashes(self, root):
        git_utils.git("init")
        article_paths = [
            'Article/en.md',
            'Article/fr.md',
            'Article/pt-br.md',
            'Article/zh-tw.md',
        ]
        article_paths_with_root = ["wiki/" + path for path in article_paths]

        conftest.create_files(root, *((path, '# Article') for path in article_paths))
        stage_all_and_commit("add an article")

        conftest.create_files(root, (article_paths[0], '# Article\n\nThis is an article in English.'))
        stage_all_and_commit("modify english article")
        commit_hash = git_utils.git("show", "HEAD", "--pretty=format:%H", "-s")

        expirer.expire_translations(*article_paths_with_root[1:], expiration_hash=commit_hash)
        stage_all_and_commit("outdate translations")

        with open(article_paths_with_root[1], "r", encoding='utf-8') as fd:
            front_matter = article_parser.load_front_matter(fd)
        front_matter[expirer.EXPIRATION_HASH_TAG] = "bogus-commit-hash"
        article_parser.save_front_matter(article_paths_with_root[1], front_matter)
        stage_all_and_commit("corrupt hash")

        assert list(expirer.check_commit_hashes(article_paths_with_root[1:])) == article_paths_with_root[1:2]
