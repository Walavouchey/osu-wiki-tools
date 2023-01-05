import abc

import yaml
import yamllint.rules  # type: ignore


ALLOWED_FRONT_MATTER_TAGS = frozenset({
    # Article tags
    "needs_cleanup",
    "layout",  # Main Page uses this
    "legal",
    "outdated",
    "outdated_since",
    "outdated_translation",
    "stub",
    "tags",
    "translate_from",  # https://github.com/ppy/osu-wiki/pull/7865/commits/ba6a169add4f3cac620e0147e81323a28cd27376

    # Newspost tags
    "date",
    "layout",
    "title",
    "tumblr_url",
})


class _JunkMatcher:
    def match_file(self, p: str):
        return not p.endswith(".md")


class _State(list):
    def start_sequence(self):
        self.append(yaml.SequenceStartEvent(None, None, False))

    def start_mapping(self):
        self.append(yaml.MappingStartEvent(None, None, False))

    def end_nested_object(self):
        if len(self) > 0:
            self.pop()

    def inside_sequence(self):
        return len(self) > 0 and isinstance(self[-1], yaml.SequenceStartEvent)

    def inside_mapping(self):
        return len(self) > 0 and isinstance(self[-1], yaml.MappingStartEvent)


class _FrontMatterRule(dict, metaclass=abc.ABCMeta):
    TYPE = "token"
    LEVEL = "error"

    @property
    @abc.abstractmethod
    def ID(self):
        raise ValueError("Missing rule identifier")

    @abc.abstractmethod
    def inner_check(
        self, state: _State, prev_token: yaml.Token, token: yaml.Token,
        next_token: yaml.Token, next_next_token: yaml.Token
    ):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self['ignore'] = _JunkMatcher()
        self['level'] = self.LEVEL

    @staticmethod
    def _is_start_of_mapping(token: yaml.Token):
        return isinstance(token, (yaml.BlockMappingStartToken, yaml.FlowMappingStartToken))

    @staticmethod
    def _is_start_of_sequence(token: yaml.Token):
        return isinstance(token, (yaml.BlockSequenceStartToken, yaml.FlowSequenceStartToken))

    @staticmethod
    def _is_end_of_nested_block(token: yaml.Token):
        return isinstance(token, (yaml.BlockEndToken, yaml.FlowMappingEndToken, yaml.FlowSequenceEndToken))

    @staticmethod
    def _is_mapping_key(prev_token: yaml.Token, token: yaml.Token, next_token: yaml.Token):
        return (
            isinstance(prev_token, yaml.KeyToken) and isinstance(token, yaml.ScalarToken) and
            isinstance(next_token, yaml.ValueToken)
        )

    @classmethod
    def _make_problem(cls, next_token: yaml.Token, issue: str):
        return yamllint.linter.LintProblem(
            next_token.start_mark.line + 1, next_token.start_mark.column + 1, issue, cls.LEVEL
        )

    def check(
        self, conf: yamllint.config.YamlLintConfig, token: yaml.Token,
        prev_token: yaml.Token, next_token: yaml.Token, next_next_token: yaml.Token, context: dict
    ):
        state = context.setdefault("state", _State())
        error = self.inner_check(state, prev_token, token, next_token, next_next_token)
        if error is not None:
            yield error

        if self._is_start_of_mapping(token):
            state.start_mapping()
        elif self._is_start_of_sequence(token):
            state.start_sequence()
        elif self._is_end_of_nested_block(token):
            state.end_nested_object()


class NestedStructureRule(_FrontMatterRule):
    ID = "osu-wiki-nested-structure"

    def inner_check(
        self, state: _State, prev_token: yaml.Token, token: yaml.Token,
        next_token: yaml.Token, next_next_token: yaml.Token
    ):
        # "tags", the top-level list of article tags, is the only field allowed to contain lists
        allowed_combination = state.inside_mapping() and self._is_start_of_sequence(token)
        if (
            (state.inside_mapping() or state.inside_sequence()) and
            (self._is_start_of_mapping(token) or self._is_start_of_sequence(token)) and
            not allowed_combination
        ):
            return self._make_problem(
                next_token,
                "bad front matter: lists or dictionaries cannot contain other similarly complex objects"
            )


class TopLevelRule(_FrontMatterRule):
    ID = "osu-wiki-top-level"

    def inner_check(
        self, state: _State, prev_token: yaml.Token, token: yaml.Token,
        next_token: yaml.Token, next_next_token: yaml.Token
    ):
        if self._is_start_of_sequence(token) and len(state) == 0:
            return self._make_problem(next_token, "bad front matter: the top level must be a dictionary, not a list")


class AllowedTagsRule(_FrontMatterRule):
    ID = "osu-wiki-allowed-tags"

    def inner_check(
        self, state: _State, prev_token: yaml.Token, token: yaml.Token,
        next_token: yaml.Token, next_next_token: yaml.Token
    ):
        if self._is_mapping_key(prev_token, token, next_token):
            value = token.value  # type: ignore
            if value not in ALLOWED_FRONT_MATTER_TAGS:
                return self._make_problem(token, f"bad front matter: {value!r} is not in the list of allowed tags")
