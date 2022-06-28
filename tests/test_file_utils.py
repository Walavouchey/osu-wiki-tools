from collections import Counter as multiset
import os

import conftest
import utils

from wikitools import file_utils

class TestFileUtils:
    def test__list_all_article_files(self, root):
        article_paths = [
            'wiki/Article/en.md',
            'wiki/Article/fr.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
            'wiki/Article/TRANSLATING.md',
            'wiki/Article/TEMPLATE.md',
            'wiki/Category1/Article/en.md',
            'wiki/Category1/Article/fr.md',
            'wiki/Category1/Article/pt-br.md',
            'wiki/Category1/Article/zh-tw.md',
            'wiki/Category1/Category2/Article/en.md',
            'wiki/Category1/Category2/Article/fr.md',
            'wiki/Category1/Category2/Article/pt-br.md',
            'wiki/Category1/Category2/Article/zh-tw.md',
            'wiki/Category1/Category2/Category3/Article/en.md',
            'wiki/Category1/Category2/Category3/Article/fr.md',
            'wiki/Category1/Category2/Category3/Article/pt-br.md',
            'wiki/Category1/Category2/Category3/Article/zh-tw.md',
        ]

        utils.create_files(root, *((path, '# Article') for path in article_paths))

        assert multiset(file_utils.list_all_article_files()) == multiset(utils.remove(article_paths, "TEMPLATE.md", "TRANSLATING.md"))

    def test__list_all_article_dirs(self, root):
        article_paths = [
            'wiki/Article/en.md',
            'wiki/Article/fr.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
            'wiki/Article/TRANSLATING.md',
            'wiki/Article/TEMPLATE.md',
            'wiki/Category1/Article/en.md',
            'wiki/Category1/Article/fr.md',
            'wiki/Category1/Article/pt-br.md',
            'wiki/Category1/Article/zh-tw.md',
            'wiki/Category1/Category2/Article/en.md',
            'wiki/Category1/Category2/Article/fr.md',
            'wiki/Category1/Category2/Article/pt-br.md',
            'wiki/Category1/Category2/Article/zh-tw.md',
            'wiki/Category1/Category2/Category3/Article/en.md',
            'wiki/Category1/Category2/Category3/Article/fr.md',
            'wiki/Category1/Category2/Category3/Article/pt-br.md',
            'wiki/Category1/Category2/Category3/Article/zh-tw.md',
        ]

        utils.create_files(root, *((path, '# Article') for path in article_paths))

        assert multiset(file_utils.list_all_article_dirs()) == multiset(set(os.path.dirname(path) for path in article_paths))

    def test__list_all_translations(self, root):
        article_paths = [
            'wiki/Article/en.md',
            'wiki/Article/fr.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
            'wiki/Article/TRANSLATING.md',
            'wiki/Article/TEMPLATE.md',
        ]

        utils.create_files(root, *((path, '# Article') for path in article_paths))

        assert multiset(file_utils.list_all_translations(["wiki/Article"])) == multiset(article_paths[1:4])

