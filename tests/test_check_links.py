import tests.conftest
import tests.utils as utils

from wikitools_cli.commands import check_links as link_checker


class TestCheckLinks:
    def test__check_links_all_valid(self, root):
        article_paths = [
            'wiki/redirect.yaml',
            'wiki/Article/en.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
            'wiki/Category1/Article/en.md',
            'wiki/Category1/Article/fr.md',
            'wiki/Category1/Article/zh-tw.md',
            'wiki/Category1/Article/TEMPLATE.md',
            'news/newspost.md',
        ]

        utils.create_files(root, *((path, '[good link](/wiki/Article)') for path in article_paths))
        utils.create_files(root, ('wiki/Article/img/image.png', b'\x89PNG'))

        exit_code = link_checker.main("--all")
        assert exit_code == 0

    def test__check_links_all_invalid(self, root):
        article_paths = [
            'wiki/redirect.yaml',
            'wiki/Article/en.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
            'wiki/Category1/Article/en.md',
            'wiki/Category1/Article/fr.md',
            'wiki/Category1/Article/zh-tw.md',
            'wiki/Category1/Article/TEMPLATE.md',
            'news/newspost.md',
        ]

        utils.create_files(root, *((path, '[bad link](/wiki/Not_an_article)') for path in article_paths))
        utils.create_files(root, ('wiki/Article/img/image.png', b'\x89PNG'))

        exit_code = link_checker.main("--all")
        assert exit_code == 1

    def test__check_links_all_valid_with_changed_root(self, root):
        article_paths = [
            'root/wiki/redirect.yaml',
            'root/wiki/Article/en.md',
            'root/wiki/Article/pt-br.md',
            'root/wiki/Article/zh-tw.md',
            'root/wiki/Category1/Article/en.md',
            'root/wiki/Category1/Article/fr.md',
            'root/wiki/Category1/Article/zh-tw.md',
            'root/wiki/Category1/Article/TEMPLATE.md',
            'root/news/newspost.md',
        ]

        utils.create_files(root, *((path, '[good link](/wiki/Article)') for path in article_paths))
        utils.create_files(root, ('root/wiki/Article/img/image.png', b'\x89PNG'))

        exit_code = link_checker.main("--all", "--root", "root")
        assert exit_code == 0

    def test__check_links_all_invalid_with_changed_root(self, root):
        article_paths = [
            'root/wiki/redirect.yaml',
            'root/wiki/Article/en.md',
            'root/wiki/Article/pt-br.md',
            'root/wiki/Article/zh-tw.md',
            'root/wiki/Category1/Article/en.md',
            'root/wiki/Category1/Article/fr.md',
            'root/wiki/Category1/Article/zh-tw.md',
            'root/wiki/Category1/Article/TEMPLATE.md',
            'root/news/newspost.md',
        ]

        utils.create_files(root, *((path, '[bad link](/wiki/Not_an_article)') for path in article_paths))
        utils.create_files(root, ('root/wiki/Article/img/image.png', b'\x89PNG'))

        exit_code = link_checker.main("--all", "--root", "root")
        assert exit_code == 1
