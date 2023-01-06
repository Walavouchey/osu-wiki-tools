import textwrap

import yaml
import yamllint.config  # type: ignore
from yamllint import linter  # type: ignore
from yamllint.rules import key_duplicates  # type: ignore

import pytest
import unittest.mock

import tests.utils as utils

from wikitools import article_parser
from wikitools import yaml_rules
from wikitools_cli.commands import check_yaml

@pytest.fixture
def linter_config():
    cfg = yamllint.config.YamlLintConfig(check_yaml.DEFAULT_CONFIG_CONTENT)
    check_yaml.install_custom_checks(cfg)
    yield cfg


@pytest.fixture
def front_matter():
    def front_matter_maker(*dicts):
        dumps = "".join(
            yaml.dump(d, default_flow_style=False, sort_keys=True, indent=2, Dumper=article_parser.Dumper)
            for d in dicts
        )
        return "---\n{}---\n".format(dumps)

    yield front_matter_maker


class TestYamlRules:
    def test__duplicate_keys(self, linter_config, front_matter):
        fm = front_matter(
            dict(outdated=True, tags=[1, 2, 3]),
            dict(outdated=True, outdated_translation=True)
        )
        issue = next(linter.run(fm, linter_config))
        assert issue.rule == key_duplicates.ID

    def test__unknown_tags(self, linter_config, front_matter):
        fm = front_matter(
            dict(outdate=True, needs_cleanup=True, taggs=[1, 2])
        )
        first_issue, second_issue = list(linter.run(fm, linter_config))

        assert first_issue.rule == yaml_rules.AllowedTagsRule.ID
        assert first_issue.line == 3 and first_issue.column == 1  # "---" -> "needs_cleanup: true" -> "outdate: true"
        assert first_issue.level == 'error'
        assert "'outdate'" in first_issue.message

        assert second_issue.rule == yaml_rules.AllowedTagsRule.ID
        assert second_issue.line == 4 and second_issue.column == 1  # "---" -> "needs_cleanup: true" -> "outdate: true"
        assert second_issue.level == 'error'
        assert "'taggs'" in second_issue.message

    @pytest.mark.parametrize(
        "payload",
        [
            {"outdated": {"outdated": True}},
            {"tags": [["some-tag", "some-tag-2"], "some-tag-3"]},
            {"tags": [{"outdated": True}, "some-tag"]}
        ]
    )
    def test__bad_nesting(self, linter_config, front_matter, payload):
        fm = front_matter(payload)
        issue = next(linter.run(fm, linter_config))

        assert issue.rule == yaml_rules.NestedStructureRule.ID
        assert issue.line == 3  # points at the first nested element
        assert issue.level == 'error'

    def test__good_nesting(self, linter_config, front_matter, mocker: unittest.mock.Mock):
        rule = linter_config.rules[yaml_rules.NestedStructureRule.ID]
        rule.inner_check = mocker.Mock(side_effect=rule.inner_check)

        fm = front_matter(dict(tags=[1, 2, 3]))
        with pytest.raises(StopIteration):
            _ = next(linter.run(fm, linter_config))

        assert rule.inner_check.called

    def test__bad_top_level(self, linter_config, front_matter):
        fm = front_matter([
            "outdated",
            True,
        ])
        issue = next(linter.run(fm, linter_config))

        assert issue.rule == yaml_rules.TopLevelRule.ID
        assert issue.line == 2
        assert issue.level == 'error'

    def test__cli__read_front_matter(self, linter_config, root):
        utils.create_files(
            root,
            (
                'wiki/Article/en.md',
                textwrap.dedent('''
                    ---
                    stub: true
                    unknown_tag: true
                    tags:
                        - outdated: true
                    ---

                    # An article
                ''').strip()
            )
        )

        fm = check_yaml.read_yaml(str(root / 'wiki/Article/en.md'))
        tag_issue, nesting_issue = list(linter.run(fm, linter_config))

        assert tag_issue.rule == yaml_rules.AllowedTagsRule.ID
        assert tag_issue.line == 3

        assert nesting_issue.rule == yaml_rules.NestedStructureRule.ID
        assert nesting_issue.line == 5
