import collections
import textwrap

import conftest

from wikitools import article_parser, git_utils

from wikitools_cli import check_outdated_articles as outdater


def stage_all_and_commit(commit_message):
    git_utils.git("add", ".")
    git_utils.git("commit", "-m", commit_message)


def set_up_dummy_repo():
    git_utils.git("init")
    git_utils.git("config", "user.name", "John Smith")
    git_utils.git("config", "user.email", "john.smith@example.com")


class TestArticleOutdater:
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

        assert collections.Counter(outdater.list_all_translations(["wiki/Article"])) == collections.Counter(article_paths_with_root[1:4])

    def test__list_modified_translations(self, root):
        set_up_dummy_repo()
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

        modified_translations = outdater.list_modified_translations(commit_hash)
        assert collections.Counter(modified_translations) == collections.Counter(filter(lambda x : "en.md" not in x, article_paths_with_root))

        conftest.create_files(root,
            *((path, '# Article\n\nCeci est un article en français.') for path in
            list(filter(lambda x : "fr.md" in x, article_paths)))
        )
        stage_all_and_commit("add article content")
        commit_hash = git_utils.git("show", "HEAD", "--pretty=format:%H", "-s")

        modified_translations = outdater.list_modified_translations(commit_hash)
        assert collections.Counter(modified_translations) == collections.Counter(filter(lambda x : "fr.md" in x, article_paths_with_root))

    def test__list_modified_originals(self, root):
        set_up_dummy_repo()
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

        modified_originals = outdater.list_modified_originals(commit_hash)
        assert collections.Counter(modified_originals) == collections.Counter(article_paths_with_root[0:2])


    def test__list_outdated_translations(self, root):
        set_up_dummy_repo()
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

        conftest.create_files(root, *zip(article_paths[0:2], [
            '# Article\n\nThis is an article in English.',
            '# Article\n\nThis is another article in English.',
        ]))
        stage_all_and_commit("add english article content")
        commit_hash = git_utils.git("show", "HEAD", "--pretty=format:%H", "-s")
        translations_to_outdate = list(outdater.list_outdated_translations(
            filter(lambda x : "en.md" not in x, article_paths_with_root),
            ()
        ))

        assert collections.Counter(translations_to_outdate) == collections.Counter(filter(lambda x : "en.md" not in x, article_paths_with_root))


    def test__outdate_translations(self, root):
        set_up_dummy_repo()
        article_paths = [
            'Article2/en.md',
            'Article/en.md',
            'Article2/fr.md',
            'Article/fr.md',
            'Article2/pt-br.md',
            'Article/pt-br.md',
            'Article2/zh-tw.md',
            'Article/zh-tw.md',
        ]
        article_paths_with_root = ["wiki/" + path for path in article_paths]

        conftest.create_files(root, *((path, '# Article') for path in article_paths))
        stage_all_and_commit("add some articles")

        conftest.create_files(root, *zip(article_paths[0:2], [
            '# Article\n\nThis is an article in English.',
            '# Article\n\nThis is another article in English.',
        ]))
        stage_all_and_commit("add english article content")
        commit_hash = git_utils.git("show", "HEAD", "--pretty=format:%H", "-s")

        to_outdate_zh_tw = list(filter(lambda x : "zh-tw.md" in x, article_paths_with_root))
        outdater.outdate_translations(*to_outdate_zh_tw, outdated_hash=commit_hash)
        outdated_translations = git_utils.git("diff", "--diff-filter=d", "--name-only").splitlines()
        stage_all_and_commit("outdate zh-tw")

        assert collections.Counter(outdated_translations) == collections.Counter(to_outdate_zh_tw)

        to_outdate_all = list(filter(lambda x : "en.md" not in x, article_paths_with_root))
        outdater.outdate_translations(*to_outdate_all, outdated_hash=commit_hash)
        outdated_translations = git_utils.git("diff", "--diff-filter=d", "--name-only").splitlines()
        stage_all_and_commit("outdate the rest of the translations")

        assert collections.Counter(outdated_translations) == collections.Counter(to_outdate_all) - collections.Counter(to_outdate_zh_tw)

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
        set_up_dummy_repo()
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

        outdater.outdate_translations(*article_paths_with_root[1:], outdated_hash=commit_hash)
        stage_all_and_commit("outdate translations")

        with open(article_paths_with_root[1], "r", encoding='utf-8') as fd:
            front_matter = article_parser.load_front_matter(fd)
        front_matter[outdater.OUTDATED_HASH_TAG] = "bogus-commit-hash"
        article_parser.save_front_matter(article_paths_with_root[1], front_matter)
        stage_all_and_commit("corrupt hash")

        assert collections.Counter(outdater.check_commit_hashes(article_paths_with_root[1:])) == collections.Counter(article_paths_with_root[1:2])

    def test__full_autofix_flow(self, root):
        set_up_dummy_repo()
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

        conftest.create_files(root, *((path, '# Article') for path in article_paths))
        stage_all_and_commit("add articles")
        commit_hash_1 = git_utils.git("show", "HEAD", "--pretty=format:%H", "-s")

        already_outdated_translations = list(filter(lambda x : "zh-tw.md" in x, article_paths_with_root))
        outdater.outdate_translations(*already_outdated_translations, outdated_hash=commit_hash_1)
        stage_all_and_commit("outdate chinese translations")

        conftest.create_files(root, *(
            (article_path, '# Article\n\nThis is an article in English.') for article_path in
            filter(lambda x : "en.md" in x, article_paths)
        ))
        stage_all_and_commit("modify english articles")
        commit_hash_2 = git_utils.git("show", "HEAD", "--pretty=format:%H", "-s")


        exit_code = outdater.main("--base-commit", commit_hash_2, f"--{outdater.AUTOFIX_FLAG}")

        assert exit_code == 0

        outdated_translations = git_utils.git("diff", "--diff-filter=d", "--name-only").splitlines()

        non_chinese_translations = filter(lambda x : "en.md" not in x and "zh-tw.md" not in x, article_paths_with_root)
        assert collections.Counter(outdated_translations) == collections.Counter(non_chinese_translations)

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

        for article in filter(lambda x : "en.md" in x, article_paths_with_root):
            with open(article, "r", encoding='utf-8') as fd:
                content = fd.read()

            assert content == '# Article\n\nThis is an article in English.'

        log = git_utils.git("--no-pager", "log", "--pretty=oneline").splitlines()

        assert len(log) == 3
