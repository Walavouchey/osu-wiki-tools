from collections import Counter as multiset
import os

import conftest
import utils

from wikitools import file_utils

class TestFileUtils:
    def test__list_all_article_files(self, root):
        article_paths = [
            'Article/en.md',
            'Article/fr.md',
            'Article/pt-br.md',
            'Article/zh-tw.md',
            'Article/TRANSLATING.md',
            'Article/TEMPLATE.md',
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

        utils.create_files(root, *((path, '# Article') for path in article_paths))

        assert multiset(list(file_utils.list_all_article_files())) == multiset(utils.remove(article_paths_with_root, "TEMPLATE.md", "TRANSLATING.md"))

    def test__list_all_article_dirs(self, root):
        article_paths = [
            'Article/en.md',
            'Article/fr.md',
            'Article/pt-br.md',
            'Article/zh-tw.md',
            'Article/TRANSLATING.md',
            'Article/TEMPLATE.md',
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

        utils.create_files(root, *((path, '# Article') for path in article_paths))

        assert multiset(file_utils.list_all_article_dirs()) == multiset(set(os.path.dirname(path) for path in article_paths_with_root))

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

        utils.create_files(root, *((path, '# Article') for path in article_paths))

        assert multiset(file_utils.list_all_translations(["wiki/Article"])) == multiset(article_paths_with_root[1:4])

