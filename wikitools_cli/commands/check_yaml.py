#!/usr/bin/env python3

import argparse
import os
import sys
import typing

import yamllint.cli  # type: ignore
import yamllint.config  # type: ignore
import yamllint.linter  # type: ignore
import yamllint.rules  # type: ignore

from wikitools import console
from wikitools import yaml_rules

FRONT_MATTER_DELIMITER = "---"
MARKDOWN_EXTENSION = ".md"

DEFAULT_CONFIG_CONTENT = 'extends: default'


def install_custom_checks(config: yamllint.config.YamlLintConfig):
    for rule_cls in yaml_rules.OSU_WIKI_RULES:
        config.rules[rule_cls.ID] = yamllint.rules._RULES[rule_cls.ID] = rule_cls()


def front_matter(fileobj: typing.TextIO, filepath: str) -> str:
    delimiters = 0
    lines = []
    for line in fileobj:
        if line.split("#")[0].strip() == FRONT_MATTER_DELIMITER:
            delimiters += 1
        # Stop on second delimiter, or when it's clear there won't be front matter at all
        if delimiters == 2 or line.startswith("# "):
            break
        lines.append(line)

    if delimiters == 0:
        return ""
    if delimiters == 2:
        return "".join(lines)
    raise ValueError(f"The file {filepath} has malformed front matter")


def read_yaml(filepath: str):
    with open(filepath, "r", encoding='utf-8') as fd:
        if filepath.endswith(MARKDOWN_EXTENSION):
            return front_matter(fd, filepath)
        else:
            return fd.read()


def file_iterator(roots: list, config: yamllint.config.YamlLintConfig):
    for item in roots:
        if os.path.isdir(item):
            for root, _, filenames in os.walk(item):
                for f in filenames:
                    filepath = os.path.join(root, f)
                    if (
                        not config.is_file_ignored(filepath) and
                        (config.is_yaml_file(filepath) or filepath.endswith(MARKDOWN_EXTENSION))
                    ):
                        yield filepath
        elif os.path.isfile(item):
            yield item


def parse_args(args: list):
    parser = argparse.ArgumentParser(
        description="Check YAML files and front matter of the Markdown documents for common mistakes"
    )
    parser.add_argument("--config", help="path to the yamllint config", default="./.yamllint.yaml")
    parser.add_argument(
        "--target", nargs="+", default=(".",),
        help="files or directories to lint (by default, assumes current working directory)"
    )
    parser.add_argument("--format", choices=("parsable", "standard", "colored", "github", "auto"),
        default="colored", help="output format (see yamllint docs for details)"
    )
    return parser.parse_args(args)


def main(*args):
    args = parse_args(args)
    if os.path.exists(args.config):
        config = yamllint.config.YamlLintConfig(file=os.path.expanduser(args.config))
    else:
        config = yamllint.config.YamlLintConfig(DEFAULT_CONFIG_CONTENT)

    install_custom_checks(config)

    max_level = 0
    for path in file_iterator(args.target, config):
        try:
            path = path[2:] if path.startswith('./') else path
            payload = read_yaml(path)
            problems = yamllint.linter.run(payload, config, path)
        except EnvironmentError as e:
            print(e, file=sys.stderr)
            sys.exit(-1)
        current_level = yamllint.cli.show_problems(problems, path, args_format=args.format, no_warn=False)
        max_level = max(max_level, current_level)

    if max_level == yamllint.linter.PROBLEM_LEVELS["error"]:
        sys.exit(1)

    print(f"{console.grey('Notice:')} No errors in YAML files detected.")


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
