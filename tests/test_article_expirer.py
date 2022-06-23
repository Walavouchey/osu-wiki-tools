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


def get_changed_files():
    return git_utils.git("diff", "--diff-filter=d", "--name-only").splitlines()


def get_last_commit_hash():
    return git_utils.git("show", "HEAD", "--pretty=format:%H", "-s")


def has_same_elements(a, b):
    return collections.Counter(a) == collections.Counter(b)


def take(the_list, *may_contain):
    return list(filter(lambda item : any(thing in item for thing in may_contain), the_list))


def remove(the_list, *may_not_contain):
    return list(filter(lambda item : all(thing not in item for thing in may_not_contain), the_list))


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

        assert has_same_elements(outdater.list_all_translations(["wiki/Article"]), article_paths_with_root[1:4])

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
        commit_hash = get_last_commit_hash()

        modified_translations = outdater.list_modified_translations(commit_hash)

        assert has_same_elements(modified_translations, remove(article_paths_with_root, "en.md"))

        conftest.create_files(root,
            *((path, '# Article\n\nCeci est un article en français.') for path in
            take(article_paths, "fr.md"))
        )
        stage_all_and_commit("add article content")
        commit_hash = get_last_commit_hash()

        modified_translations = outdater.list_modified_translations(commit_hash)

        assert has_same_elements(modified_translations, take(article_paths_with_root, "fr.md"))

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
        commit_hash = get_last_commit_hash()

        conftest.create_files(root, *zip(article_paths[0:2], [
            '# Article\n\nThis is an article in English.',
            '# Article\n\nThis is another article in English.',
        ]))
        stage_all_and_commit("add article content")
        commit_hash = get_last_commit_hash()

        modified_originals = outdater.list_modified_originals(commit_hash)
        assert has_same_elements(modified_originals, take(article_paths_with_root, "en.md"))

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
        commit_hash = get_last_commit_hash()
        translations_to_outdate = list(outdater.list_outdated_translations(
            set(remove(article_paths_with_root, "en.md")),
            set()
        ))

        assert has_same_elements(translations_to_outdate, remove(article_paths_with_root, "en.md"))

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
        commit_hash = get_last_commit_hash()

        to_outdate_zh_tw = take(article_paths_with_root, "zh-tw.md")
        outdater.outdate_translations(*to_outdate_zh_tw, outdated_hash=commit_hash)
        outdated_translations = get_changed_files()
        stage_all_and_commit("outdate zh-tw")

        assert has_same_elements(outdated_translations, to_outdate_zh_tw)

        to_outdate_all = remove(article_paths_with_root, "en.md")
        outdater.outdate_translations(*to_outdate_all, outdated_hash=commit_hash)
        outdated_translations = get_changed_files()
        stage_all_and_commit("outdate the rest of the translations")

        assert has_same_elements(outdated_translations, remove(article_paths_with_root, "en.md", "zh-tw.md"))

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
        commit_hash = get_last_commit_hash()

        outdater.outdate_translations(*article_paths_with_root[1:], outdated_hash=commit_hash)
        stage_all_and_commit("outdate translations")

        with open(article_paths_with_root[1], "r", encoding='utf-8') as fd:
            front_matter = article_parser.load_front_matter(fd)
        front_matter[outdater.OUTDATED_HASH_TAG] = "bogus-commit-hash"
        article_parser.save_front_matter(article_paths_with_root[1], front_matter)
        stage_all_and_commit("corrupt hash")

        assert has_same_elements(outdater.check_commit_hashes(article_paths_with_root[1:]), article_paths_with_root[1:2])

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
        commit_hash_1 = get_last_commit_hash()

        already_outdated_translations = take(article_paths_with_root, "zh-tw.md")
        outdater.outdate_translations(*already_outdated_translations, outdated_hash=commit_hash_1)
        stage_all_and_commit("outdate chinese translations")

        conftest.create_files(root, *(
            (article_path, '# Article\n\nThis is an article in English.') for article_path in
            take(article_paths, "en.md")
        ))
        stage_all_and_commit("modify english articles")
        commit_hash_2 = get_last_commit_hash()


        exit_code = outdater.main("--base-commit", commit_hash_2, f"--{outdater.AUTOFIX_FLAG}")

        assert exit_code == 0

        outdated_translations = get_changed_files()

        non_chinese_translations = remove(article_paths_with_root, "en.md", "zh-tw.md")

        assert has_same_elements(outdated_translations, non_chinese_translations)

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

        for article in take(article_paths_with_root, "en.md"):
            with open(article, "r", encoding='utf-8') as fd:
                content = fd.read()

            assert content == '# Article\n\nThis is an article in English.'

        log = git_utils.git("--no-pager", "log", "--pretty=oneline").splitlines()

        assert len(log) == 3
