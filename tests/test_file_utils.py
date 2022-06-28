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

        assert multiset(file_utils.list_all_articles()) == multiset(utils.remove(article_paths, "TEMPLATE.md", "TRANSLATING.md"))

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

    def test_list_all_articles_and_newsposts(self, root):
        article_paths = [
            'wiki/Article/en.md',
            'wiki/Article/fr.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
            'wiki/Article/TRANSLATING.md',
            'wiki/Article/TEMPLATE.md',
        ]

        newspost_paths = [
            'news/2022-06-23-project-loved-june-2022.md',
            'news/2023-09-22-first-world-cup-held-using-lazer.md',
            'news/2024-05-15-2b-maps-are-now-rankable.md',
            'news/2025-12-20-trivium-quiz-winners.md',
            'news/2026-03-12-second-annual-pp-committee-meeting.md',
            'news/2027-02-08-the-old-client-is-now-deprecated.md',
            'news/2028-07-28-introducing-osu-lite-smartwatch-edition.md',
            '.remarkrc.js'
        ]

        utils.create_files(root, *((path, '# Article') for path in article_paths))
        utils.create_files(root, *((path, '# News post') for path in newspost_paths))

        assert multiset(file_utils.list_all_articles_and_newsposts()) == multiset(article_paths[0:4] + newspost_paths[0:-1])
