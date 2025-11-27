import json

import pytest
import tests.utils as utils
from tests.utils import OutputCapture

from wikitools_cli.commands import front_matter


class TestEditFrontMatter:
    @pytest.mark.parametrize(
        "payload",
        [
            {
                "path": "wiki/None/en.md",
                "content": "# Article",
                "args": ("--set", "layout:post"),
                "expected": "---\nlayout: post\n---\n\n# Article"
            },
            {
                "path": "wiki/Has/en.md",
                "content": "---\ntitle: test\n---\n\n# Article",
                "args": ("--set", "layout:post"),
                "expected": "---\ntitle: test\nlayout: post\n---\n\n# Article"
            },
            {
                "path": "wiki/Existing/en.md",
                "content": "---\ntitle: bad\n---\n\n# Article",
                "args": ("--set", "title:good"),
                "expected": "---\ntitle: good\n---\n\n# Article"
            },
            {
                "path": "wiki/Quoted/en.md",
                "content": "---\ntitle: unquoted\n---\n\n# Article",
                "args": ("--set", "title:unquoted 2: electric boogaloo"),
                "expected": "---\ntitle: \"unquoted 2: electric boogaloo\"\n---\n\n# Article"
            },
            {
                "path": "wiki/Remove/en.md",
                "content": "---\ntag: bye\n---\n\n# Article",
                "args": ("--remove", "tag"),
                "expected": "# Article"
            },
            {
                "path": "wiki/Remove_multiple/en.md",
                "content": "---\ntag: bye\nseries: yep\n---\n\n# Article",
                "args": ("--remove", "tag", "series"),
                "expected": "# Article"
            },
        ]
    )
    def test__edit_front_matter(self, root, payload):
        utils.create_files(root, (payload["path"], payload["content"]))

        exit_code = front_matter.main(payload["path"], *payload["args"])
        assert exit_code == 0

        with open(payload["path"], "r", encoding="utf-8") as file:
            content = file.read()

        assert content == payload["expected"]

    @pytest.mark.parametrize(
        "payload",
        [
            {
                "path": "wiki/None/en.md",
                "content": "# Article",
                "args": ("--print", "title"),
                "expected": {"title": None}
            },
            {
                "path": "wiki/Some/en.md",
                "content": "---\ntitle: test\n---\n\n# Article",
                "args": ("--print", "title"),
                "expected": {"title": "test"}
            },
            {
                "path": "wiki/Multiple/en.md",
                "content": "---\ntitle: cookies\nseries: cooking\n---\n\n# Article",
                "args": ("--print", "title", "series"),
                "expected": {"title": "cookies", "series": "cooking"}
            },
            {
                "path": "wiki/Partial/en.md",
                "content": "---\ntitle: cookies\n---\n\n# Article",
                "args": ("--print", "title", "series"),
                "expected": {"title": "cookies", "series": None}
            },
            {
                "path": "wiki/All/en.md",
                "content": "---\ntitle: cookies\nseries: cooking\n---\n\n# Article",
                "args": ("--print",),
                "expected": {"title": "cookies", "series": "cooking"}
            },
        ]
    )
    def test_print_front_matter(self, root, payload):
        utils.create_files(root, (payload["path"], payload["content"]))

        with OutputCapture() as out:
            exit_code = front_matter.main(payload["path"], *payload["args"])

        assert exit_code == 0
        assert out.stderr == ""
        assert json.loads(out.stdout) == payload["expected"]
