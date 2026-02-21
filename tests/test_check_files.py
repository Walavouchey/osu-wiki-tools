import tests.utils as utils

import pytest

from wikitools_cli.commands import check_files as file_checker


class TestCheckFiles:
    @pytest.mark.parametrize(
        "format",
        [
            "regular",
            "json",
            "github",
        ]
    )
    def test__check_files_all_valid(self, root, format):
        article_paths = [
            'wiki/redirect.yaml',
            'wiki/Article/en.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
            'wiki/Category1/Article/en.md',
            'wiki/Category1/Article/fr.md',
            'wiki/Category1/Article/zh-tw.md',
            'wiki/Category1/Article/TEMPLATE.md',
            'news/2023/newspost.md',
        ]

        utils.create_files(root, *((path, '') for path in article_paths))

        exit_code = file_checker.main("--all", "--format", format)
        assert exit_code == 0

    @pytest.mark.parametrize(
        "format",
        [
            "regular",
            "json",
            "github",
        ]
    )
    def test__check_files_missing_english_version(self, root, format):
        article_paths = [
            'wiki/Article/pt-br.md',
        ]

        utils.create_files(root, *((path, '') for path in article_paths))

        exit_code = file_checker.main("--all", "--format", format)
        assert exit_code == 1
