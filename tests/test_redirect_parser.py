import textwrap

from wikitools import redirect_parser


class TestRedirectParser:
    def test__parse_redirects(self, tmpdir):
        path = tmpdir.join('redirect.yaml')
        path.write(textwrap.dedent('''
            # some junk on top

            "asc": "Article_Styling_Criteria"
            "asc/images": "Article_Styling_Criteria#images"

            "ignore_list": "Client/Options/Ignore_list"
            "ignore":      "Client/Options/Ignore_list"
            unquoted_key1:  unquoted/value1
            "quoted_key": unquoted/value2
            unquoted_key2:    "quoted/value"
        ''').strip())

        redirects = redirect_parser.load_redirects(str(path))
        assert redirects == {
            'asc': ('Article_Styling_Criteria', 3),
            'asc/images': ('Article_Styling_Criteria#images', 4),
            'ignore_list': ('Client/Options/Ignore_list', 6),
            'ignore': ('Client/Options/Ignore_list', 7),
            'unquoted_key1':  ('unquoted/value1', 8),
            'quoted_key':  ('unquoted/value2', 9),
            'unquoted_key2':  ('quoted/value', 10),
        }
