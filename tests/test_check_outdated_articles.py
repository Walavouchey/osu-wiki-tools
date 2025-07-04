from collections import Counter as multiset
import textwrap

import pytest
import tests.utils as utils

from wikitools import article_parser, git_utils, file_utils

from wikitools_cli.commands import check_outdated_articles as outdater


class TestCheckOutdatedArticles:
    def test__list_modified_translations(self, root):
        utils.set_up_dummy_repo()
        article_paths = [
            'wiki/Article/en.md',
            'wiki/Article/fr.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
            'wiki/Category1/Article/en.md',
            'wiki/Category1/Article/fr.md',
            'wiki/Category1/Article/pt-br.md',
            'wiki/Category1/Article/zh-tw.md',
            'wiki/Category1/Article/TEMPLATE.md',
            'wiki/Category1/Category2/Article/en.md',
            'wiki/Category1/Category2/Article/fr.md',
            'wiki/Category1/Category2/Article/pt-br.md',
            'wiki/Category1/Category2/Article/zh-tw.md',
            'wiki/Category1/Category2/Category3/Article/en.md',
            'wiki/Category1/Category2/Category3/Article/fr.md',
            'wiki/Category1/Category2/Category3/Article/pt-br.md',
            'wiki/Category1/Category2/Category3/Article/zh-tw.md',
        ]

        utils.create_files(root, *((path, '') for path in article_paths))
        utils.stage_all_and_commit("initial commit")

        utils.create_files(root, *((path, '# Article') for path in article_paths))
        utils.stage_all_and_commit("add article title")

        modified_translations = outdater.list_modified_translations("HEAD^")

        assert multiset(modified_translations) == multiset(utils.remove(article_paths, "en.md", "TEMPLATE.md"))

        utils.create_files(
            root,
            *(
                (path, '# Article\n\nCeci est un article en français.')
                for path in utils.take(article_paths, "fr.md")
            )
        )
        utils.stage_all_and_commit("add article content")

        modified_translations = outdater.list_modified_translations("HEAD^")

        assert multiset(modified_translations) == multiset(utils.take(article_paths, "fr.md"))

    def test__list_modified_originals(self, root):
        utils.set_up_dummy_repo()
        article_paths = [
            'wiki/Article/en.md',
            'wiki/Article2/en.md',
            'wiki/Article/fr.md',
            'wiki/Article2/fr.md',
            'wiki/Article/pt-br.md',
            'wiki/Article2/pt-br.md',
            'wiki/Article/zh-tw.md',
            'wiki/Article2/zh-tw.md',
        ]

        utils.create_files(root, *((path, '# Article') for path in article_paths))
        utils.stage_all_and_commit("add some articles")

        utils.create_files(root, *zip(article_paths[0:2], [
            '# Article\n\nThis is an article in English.',
            '# Article\n\nThis is another article in English.',
        ]))
        utils.stage_all_and_commit("add article content")

        modified_originals = outdater.list_modified_originals("HEAD^")
        assert multiset(modified_originals) == multiset(utils.take(article_paths, "en.md"))

    def test__list_outdated_translations(self, root):
        utils.set_up_dummy_repo()
        article_paths = [
            'wiki/Article/en.md',
            'wiki/Article2/en.md',
            'wiki/Article/fr.md',
            'wiki/Article2/fr.md',
            'wiki/Article/pt-br.md',
            'wiki/Article2/pt-br.md',
            'wiki/Article/zh-tw.md',
            'wiki/Article2/zh-tw.md',
        ]

        utils.create_files(root, *((path, '# Article') for path in article_paths))
        utils.stage_all_and_commit("add some articles")

        utils.create_files(root, *zip(article_paths[0:2], [
            '# Article\n\nThis is an article in English.',
            '# Article\n\nThis is another article in English.',
        ]))
        utils.stage_all_and_commit("add english article content")
        translations_to_outdate = list(outdater.list_outdated_translations(
            set(utils.remove(article_paths, "en.md")),
            set()
        ))

        assert multiset(translations_to_outdate) == multiset(utils.remove(article_paths, "en.md"))

    def test__outdate_translations(self, root):
        utils.set_up_dummy_repo()
        article_paths = [
            'wiki/Article2/en.md',
            'wiki/Article/en.md',
            'wiki/Article2/fr.md',
            'wiki/Article/fr.md',
            'wiki/Article2/pt-br.md',
            'wiki/Article/pt-br.md',
            'wiki/Article2/zh-tw.md',
            'wiki/Article/zh-tw.md',
        ]

        utils.create_files(root, *((path, '# Article') for path in article_paths))
        utils.stage_all_and_commit("add some articles")

        utils.create_files(root, *zip(article_paths[0:2], [
            '# Article\n\nThis is an article in English.',
            '# Article\n\nThis is another article in English.',
        ]))
        utils.stage_all_and_commit("add english article content")
        commit_hash = utils.get_last_commit_hash()

        to_outdate_zh_tw = utils.take(article_paths, "zh-tw.md")
        outdater.outdate_translations(*to_outdate_zh_tw, outdated_hash=commit_hash)
        outdated_translations = utils.get_changed_files()
        utils.stage_all_and_commit("outdate zh-tw")

        assert multiset(outdated_translations) == multiset(to_outdate_zh_tw)

        to_outdate_all = utils.remove(article_paths, "en.md")
        outdater.outdate_translations(*to_outdate_all, outdated_hash=commit_hash)
        outdated_translations = utils.get_changed_files()
        utils.stage_all_and_commit("outdate the rest of the translations")

        assert multiset(outdated_translations) == multiset(utils.remove(article_paths, "en.md", "zh-tw.md"))

        for article in to_outdate_all:
            with open(article, "r", encoding='utf-8') as fd:
                content = fd.read()

            assert content == textwrap.dedent('''
                ---
                {}: true
                {}: {}
                ---

                # Article
            ''').strip().format(outdater.OUTDATED_TRANSLATION_TAG, outdater.OUTDATED_HASH_TAG, commit_hash)

    def test__validate_hashes(self, root):
        utils.set_up_dummy_repo()
        article_paths = [
            'wiki/Article/en.md',
            'wiki/Article/fr.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
        ]

        utils.create_files(root, *((path, '# Article') for path in article_paths))
        utils.stage_all_and_commit("add an article")

        utils.create_files(root, (article_paths[0], '# Article\n\nThis is an article in English.'))
        utils.stage_all_and_commit("modify english article")
        commit_hash = utils.get_last_commit_hash()

        outdater.outdate_translations(*article_paths[1:], outdated_hash=commit_hash)
        utils.stage_all_and_commit("outdate translations")

        with open(article_paths[1], "r", encoding='utf-8') as fd:
            front_matter = article_parser.load_front_matter(fd)
        front_matter[outdater.OUTDATED_HASH_TAG] = "bogus-commit-hash"
        article_parser.save_front_matter(article_paths[1], front_matter)
        utils.stage_all_and_commit("corrupt hash")

        assert multiset(outdater.check_commit_hashes(article_paths[1:])) == multiset(article_paths[1:2])

    def test__full_autofix_flow(self, root):
        utils.set_up_dummy_repo()
        article_paths = [
            'wiki/Article/en.md',
            'wiki/Article/fr.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
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
        utils.stage_all_and_commit("add articles")
        commit_hash_1 = utils.get_last_commit_hash()

        already_outdated_translations = utils.take(article_paths, "zh-tw.md")
        outdater.outdate_translations(*already_outdated_translations, outdated_hash=commit_hash_1)
        utils.stage_all_and_commit("outdate chinese translations")

        utils.create_files(root, *(
            (article_path, '# Article\n\nThis is an article in English.') for article_path in
            utils.take(article_paths, "en.md")
        ))
        utils.stage_all_and_commit("modify english articles")
        commit_hash_2 = utils.get_last_commit_hash()

        exit_code = outdater.main("--base-commit", "HEAD^", "--outdated-since", commit_hash_2, f"{outdater.AUTOFIX_FLAG}")

        assert exit_code == 0

        outdated_translations = utils.get_changed_files()

        non_chinese_translations = utils.remove(article_paths, "en.md", "zh-tw.md")

        assert multiset(outdated_translations) == multiset(non_chinese_translations)

        expected_content = textwrap.dedent('''
            ---
            {}: true
            {}: {}
            ---

            # Article
        ''').strip()

        for article in already_outdated_translations:
            with open(article, "r", encoding='utf-8') as fd:
                content = fd.read()

            assert content == expected_content.format(outdater.OUTDATED_TRANSLATION_TAG, outdater.OUTDATED_HASH_TAG, commit_hash_1)

        for article in outdated_translations:
            with open(article, "r", encoding='utf-8') as fd:
                content = fd.read()

            assert content == expected_content.format(outdater.OUTDATED_TRANSLATION_TAG, outdater.OUTDATED_HASH_TAG, commit_hash_2)

        for article in utils.take(article_paths, "en.md"):
            with open(article, "r", encoding='utf-8') as fd:
                content = fd.read()

            assert content == '# Article\n\nThis is an article in English.'

        log = git_utils.git("--no-pager", "log", "--pretty=oneline").splitlines()

        assert len(log) == 3

    def test__full_autocommit_flow(self, root):
        utils.set_up_dummy_repo()
        article_paths = [
            'wiki/Article/en.md',
            'wiki/Article/fr.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
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
        utils.stage_all_and_commit("add articles")
        commit_hash_1 = utils.get_last_commit_hash()

        already_outdated_translations = utils.take(article_paths, "zh-tw.md")
        outdater.outdate_translations(*already_outdated_translations, outdated_hash=commit_hash_1)
        utils.stage_all_and_commit("outdate chinese translations")

        utils.create_files(root, *(
            (article_path, '# Article\n\nThis is an article in English.') for article_path in
            utils.take(article_paths, "en.md")
        ))
        utils.stage_all_and_commit("modify english articles")
        commit_hash_2 = utils.get_last_commit_hash()

        exit_code = outdater.main("--base-commit", "HEAD^", "--outdated-since", commit_hash_2, f"{outdater.AUTOFIX_FLAG}", f"{outdater.AUTOCOMMIT_FLAG}")

        assert exit_code == 0

        assert commit_hash_2 != utils.get_last_commit_hash()

        assert utils.get_changed_files() == []

        outdated_translations = outdater.list_modified_translations("HEAD^")

        non_chinese_translations = utils.remove(article_paths, "en.md", "zh-tw.md")

        assert multiset(outdated_translations) == multiset(non_chinese_translations)

        expected_content = textwrap.dedent('''
            ---
            {}: true
            {}: {}
            ---

            # Article
        ''').strip()

        for article in already_outdated_translations:
            with open(article, "r", encoding='utf-8') as fd:
                content = fd.read()

            assert content == expected_content.format(outdater.OUTDATED_TRANSLATION_TAG, outdater.OUTDATED_HASH_TAG, commit_hash_1)

        for article in outdated_translations:
            with open(article, "r", encoding='utf-8') as fd:
                content = fd.read()

            assert content == expected_content.format(outdater.OUTDATED_TRANSLATION_TAG, outdater.OUTDATED_HASH_TAG, commit_hash_2)

        for article in utils.take(article_paths, "en.md"):
            with open(article, "r", encoding='utf-8') as fd:
                content = fd.read()

            assert content == '# Article\n\nThis is an article in English.'

        log = git_utils.git("--no-pager", "log", "--pretty=oneline").splitlines()

        assert len(log) == 4

    def test__full_autofix_flow_with_changed_root(self, root):
        utils.set_up_dummy_repo()
        article_paths = [
            'wiki/Article/en.md',
            'wiki/Article/fr.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
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
        utils.stage_all_and_commit("add articles")
        commit_hash_1 = utils.get_last_commit_hash()

        already_outdated_translations = utils.take(article_paths, "zh-tw.md")
        outdater.outdate_translations(*already_outdated_translations, outdated_hash=commit_hash_1)
        utils.stage_all_and_commit("outdate chinese translations")

        utils.create_files(root, *(
            (article_path, '# Article\n\nThis is an article in English.') for article_path in
            utils.take(article_paths, "en.md")
        ))
        utils.stage_all_and_commit("modify english articles")
        commit_hash_2 = utils.get_last_commit_hash()

        cd = file_utils.ChangeDirectory("wiki")
        exit_code = outdater.main("--root", "..", "--base-commit", "HEAD^", "--outdated-since", commit_hash_2, f"{outdater.AUTOFIX_FLAG}")
        del cd

        assert exit_code == 0

        outdated_translations = utils.get_changed_files()

        non_chinese_translations = utils.remove(article_paths, "en.md", "zh-tw.md")

        assert multiset(outdated_translations) == multiset(non_chinese_translations)

        expected_content = textwrap.dedent('''
            ---
            {}: true
            {}: {}
            ---

            # Article
        ''').strip()

        for article in already_outdated_translations:
            with open(article, "r", encoding='utf-8') as fd:
                content = fd.read()

            assert content == expected_content.format(outdater.OUTDATED_TRANSLATION_TAG, outdater.OUTDATED_HASH_TAG, commit_hash_1)

        for article in outdated_translations:
            with open(article, "r", encoding='utf-8') as fd:
                content = fd.read()

            assert content == expected_content.format(outdater.OUTDATED_TRANSLATION_TAG, outdater.OUTDATED_HASH_TAG, commit_hash_2)

        for article in utils.take(article_paths, "en.md"):
            with open(article, "r", encoding='utf-8') as fd:
                content = fd.read()

            assert content == '# Article\n\nThis is an article in English.'

        log = git_utils.git("--no-pager", "log", "--pretty=oneline").splitlines()

        assert len(log) == 3

    def test__full_autocommit_flow_with_changed_root(self, root):
        utils.set_up_dummy_repo()
        article_paths = [
            'wiki/Article/en.md',
            'wiki/Article/fr.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
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
        utils.stage_all_and_commit("add articles")
        commit_hash_1 = utils.get_last_commit_hash()

        already_outdated_translations = utils.take(article_paths, "zh-tw.md")
        outdater.outdate_translations(*already_outdated_translations, outdated_hash=commit_hash_1)
        utils.stage_all_and_commit("outdate chinese translations")

        utils.create_files(root, *(
            (article_path, '# Article\n\nThis is an article in English.') for article_path in
            utils.take(article_paths, "en.md")
        ))
        utils.stage_all_and_commit("modify english articles")
        commit_hash_2 = utils.get_last_commit_hash()

        cd = file_utils.ChangeDirectory("wiki")
        exit_code = outdater.main("--root", "..", "--base-commit", "HEAD^", "--outdated-since", commit_hash_2, f"{outdater.AUTOFIX_FLAG}", f"{outdater.AUTOCOMMIT_FLAG}")
        del cd

        assert exit_code == 0

        assert commit_hash_2 != utils.get_last_commit_hash()

        assert utils.get_changed_files() == []

        outdated_translations = outdater.list_modified_translations("HEAD^")

        non_chinese_translations = utils.remove(article_paths, "en.md", "zh-tw.md")

        assert multiset(outdated_translations) == multiset(non_chinese_translations)

        expected_content = textwrap.dedent('''
            ---
            {}: true
            {}: {}
            ---

            # Article
        ''').strip()

        for article in already_outdated_translations:
            with open(article, "r", encoding='utf-8') as fd:
                content = fd.read()

            assert content == expected_content.format(outdater.OUTDATED_TRANSLATION_TAG, outdater.OUTDATED_HASH_TAG, commit_hash_1)

        for article in outdated_translations:
            with open(article, "r", encoding='utf-8') as fd:
                content = fd.read()

            assert content == expected_content.format(outdater.OUTDATED_TRANSLATION_TAG, outdater.OUTDATED_HASH_TAG, commit_hash_2)

        for article in utils.take(article_paths, "en.md"):
            with open(article, "r", encoding='utf-8') as fd:
                content = fd.read()

            assert content == '# Article\n\nThis is an article in English.'

        log = git_utils.git("--no-pager", "log", "--pretty=oneline").splitlines()

        assert len(log) == 4

    def test__full_autofix_flow_with_invalid_outdated_since(self, root):
        utils.set_up_dummy_repo()
        article_paths = [
            'wiki/Article/en.md',
            'wiki/Article/fr.md',
            'wiki/Article/pt-br.md',
            'wiki/Article/zh-tw.md',
        ]

        utils.create_files(root, *((path, '# Article') for path in article_paths))
        utils.stage_all_and_commit("add articles")

        utils.create_files(root, *(
            (article_path, '# Article\n\nThis is an article in English.') for article_path in
            utils.take(article_paths, "en.md")
        ))
        utils.stage_all_and_commit("modify english articles")

        exit_code = outdater.main("--base-commit", "HEAD^", f"{outdater.AUTOFIX_FLAG}")

        assert exit_code == 1

        assert utils.get_changed_files() == []

    @pytest.mark.parametrize(
        "exclude_args,expected_changed_files",
        [
            pytest.param(
                # Given
                [
                    "--exclude", "wiki/First_article/fr.md",
                    "--exclude", "wiki/First_article/pt-br.md",
                ],
                # Expect
                [
                    "wiki/First_article/zh-tw.md",

                    'wiki/Second_article/fr.md',
                    'wiki/Second_article/pt-br.md',
                    'wiki/Second_article/zh-tw.md',
                ],
                id="Single file paths",
            ),

            pytest.param(
                # Given
                [
                    "--exclude", "wiki/First_article",
                ],
                # Expect
                [
                    'wiki/Second_article/fr.md',
                    'wiki/Second_article/pt-br.md',
                    'wiki/Second_article/zh-tw.md',
                ],
                id="Directory paths",
            ),

            pytest.param(
                # Given
                [
                    "--exclude", "wiki/*/fr.md",
                ],
                # Expect
                [
                    'wiki/First_article/pt-br.md',
                    'wiki/First_article/zh-tw.md',

                    'wiki/Second_article/pt-br.md',
                    'wiki/Second_article/zh-tw.md',
                ],
                id="Fnmatch masks (only star patterns)"
            ),

            pytest.param(
                # Given
                [
                    "--exclude", "wiki/{First_article,Second_article}/pt-br.md",
                    "--exclude", "wiki/First_article/{fr,zh-tw}.md",
                ],
                # Expect
                [
                    'wiki/Second_article/fr.md',
                    'wiki/Second_article/zh-tw.md',
                ],
                id="Shell brace expansion"
            ),

            pytest.param(
                # Given
                [
                    "--exclude", "no/match",
                    "--exclude", "wiki/fr.md",
                    "--exclude", "wiki/First_art",
                    "--exclude", "wiki/Second_article/es.md",
                    "--exclude", "wiki/Second_article/en.md",
                    "--exclude", "wiki/{First_article,Second_article}/jp.md",
                ],
                # Expect
                [
                    'wiki/First_article/fr.md',
                    'wiki/First_article/pt-br.md',
                    'wiki/First_article/zh-tw.md',

                    'wiki/Second_article/fr.md',
                    'wiki/Second_article/pt-br.md',
                    'wiki/Second_article/zh-tw.md',
                ],
                id="No valid matches"
            ),

            pytest.param(
                # Given
                ["--exclude", "*"],
                # Expect
                [],
                id="Ignore the whole wiki"
            ),
            pytest.param(
                # Given
                [
                    "--exclude", "wiki/First_ARTICLE/fr.md",
                    "--exclude", "wiki/First_article/PT-BR.md",
                ],
                # Expect
                [
                    "wiki/First_article/zh-tw.md",

                    'wiki/Second_article/fr.md',
                    'wiki/Second_article/pt-br.md',
                    'wiki/Second_article/zh-tw.md',
                ],
                id="Case-insensitive matching"
            ),
        ]
    )
    def test__exclude_articles_from_check(self, root, exclude_args, expected_changed_files):
        utils.set_up_dummy_repo()
        article_paths = [
            'wiki/First_article/en.md',
            'wiki/First_article/fr.md',
            'wiki/First_article/pt-br.md',
            'wiki/First_article/zh-tw.md',

            'wiki/Second_article/en.md',
            'wiki/Second_article/fr.md',
            'wiki/Second_article/pt-br.md',
            'wiki/Second_article/zh-tw.md',
        ]

        utils.create_files(root, *((path, '# Article') for path in article_paths))
        utils.stage_all_and_commit("add articles")

        utils.create_files(root, *(
            (article_path, '# Article\n\nThis is an article in English.') for article_path in
            utils.take(article_paths, "en.md")
        ))
        utils.stage_all_and_commit("modify english articles")

        exit_code = outdater.main(
            "--autofix",
            "--base-commit", "HEAD^",
            "--outdated-since", "HEAD^",
            *exclude_args
        )

        assert exit_code == 0
        assert set(utils.get_changed_files()) == set(expected_changed_files)

    @pytest.mark.parametrize(
        "exclude_args",
        [
            pytest.param(["--exclude", "wiki/Beatmap/"], id="With trailing slash"),
            pytest.param(["--exclude", "wiki/Beatmap"], id="Without trailing slash")
        ]
    )
    def test__exclude_top_level_directory_from_check(self, root, exclude_args):
        utils.set_up_dummy_repo()
        article_paths = [
            'wiki/Beatmap/en.md',
            'wiki/Beatmap/fr.md',
            'wiki/Beatmap/pt-br.md',
            'wiki/Beatmap/zh-tw.md',

            'wiki/Beatmap/Difficulty/fr.md',
            'wiki/Beatmap/Difficulty/en.md',
            'wiki/Beatmap/Difficulty/pt-br.md',
            'wiki/Beatmap/Difficulty/zh-tw.md',

            'wiki/Beatmap/Difficulty/Tiny_speck/fr.md',
            'wiki/Beatmap/Difficulty/Tiny_speck/en.md',
            'wiki/Beatmap/Difficulty/Tiny_speck/pt-br.md',
            'wiki/Beatmap/Difficulty/Tiny_speck/zh-tw.md',
        ]

        utils.create_files(root, *((path, '# Article') for path in article_paths))
        utils.stage_all_and_commit("add articles")

        utils.create_files(root, *(
            (article_path, '# Article\n\nThis is an article in English.') for article_path in
            utils.take(article_paths, "en.md")
        ))
        utils.stage_all_and_commit("modify english articles")

        exit_code = outdater.main(
            "--autofix",
            "--base-commit", "HEAD^",
            "--outdated-since", "HEAD^",
            *exclude_args
        )

        assert exit_code == 0
        assert set(utils.get_changed_files()) == set((
            'wiki/Beatmap/Difficulty/fr.md',
            'wiki/Beatmap/Difficulty/pt-br.md',
            'wiki/Beatmap/Difficulty/zh-tw.md',

            'wiki/Beatmap/Difficulty/Tiny_speck/fr.md',
            'wiki/Beatmap/Difficulty/Tiny_speck/pt-br.md',
            'wiki/Beatmap/Difficulty/Tiny_speck/zh-tw.md',
        ))
