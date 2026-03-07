
import tests.utils as utils

import pytest
import textwrap

from wikitools_cli.commands import check_yaml as yaml_checker


class TestCheckFiles:
    @pytest.mark.parametrize(
        "format",
        [
            "parsable",
            "standard",
            "colored",
            "github",
            "auto",
            "json"
        ]
    )
    @pytest.mark.parametrize(
        "payload",
        [
            {
                "path": 'wiki/Article/en.md',
                "content": textwrap.dedent('''
                    ---
                    stub: true
                    tags:
                      - tag
                    ---

                    # An article
                ''').strip()
            },
            {
                "path": 'wiki/redirect.yaml',
                "content": textwrap.dedent('''
                    # yamllint disable rule:colons

                    asc:                           Article_styling_criteria
                    asg:                           Article_styling_criteria
                    asc/images:                    Article_styling_criteria#images
                    asg/images:                    Article_styling_criteria#images
                    wiki_styling_criteria:         Article_styling_criteria
                    wsc:                           Article_styling_criteria
                ''').strip() + "\n"
            },
        ]
    )
    def test__check_yaml_valid(self, root, format, payload):
        utils.create_files(root, (payload["path"], payload["content"]))

        exit_code = yaml_checker.main("--format", format)
        assert exit_code == 0

    @pytest.mark.parametrize(
        "format",
        [
            "parsable",
            "standard",
            "colored",
            "github",
            "auto",
            "json"
        ]
    )
    @pytest.mark.parametrize(
        "payload",
        [
            {
                "path": 'wiki/Article/en.md',
                "content": textwrap.dedent('''
                    ---
                    stub: true
                    unknown_tag: true
                    tags:
                        - outdated: true
                    ---

                    # An article
                ''').strip()
            },
            {
                "path": 'wiki/redirect.yaml',
                "content": textwrap.dedent('''
                    # definitely not valid yaml all around

                    "asc": "Article_Styling_Criteria"
                    "asc/images": "Article_Styling_Criteria#images"

                    "ignore_list": "Client/Options/Ignore_list"
                    "ignore":      "Client/Options/Ignore_list"
                    unquoted_key1:  unquoted/value1
                    "quoted_key": unquoted/value2
                    unquoted_key2:    "quoted/value"
                    osu!:    "Disambiguation/osu!"
                    osu!:rules:    "Rules"
                ''').strip()
            },
        ]
    )
    def test__check_yaml_invalid(self, root, format, payload):
        utils.create_files(root, (payload["path"], payload["content"]))

        exit_code = yaml_checker.main("--format", format)
        assert exit_code == 1
