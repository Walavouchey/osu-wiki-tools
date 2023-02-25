import pytest
import textwrap

import tests.conftest
import tests.utils as utils

from wikitools_cli.commands import generate_templates as template_generator

class TestGenerateTemplates:
    @pytest.mark.parametrize(
        "extra",
        [
            ('\n\n| existing table (deleted)', '\n\ncontent\n\nmore content'),
            ('', ''),
            ('', '\n\ncontent'),
            ('\n\n| existing table (deleted)', ''),
            ('\n\n| existing table (deleted)', '\n\ncontent'),
        ]
    )
    def test__generate_template(self, root, extra):
        csv_file = ('meta/data/originals.csv', textwrap.dedent('''
            Track,Type,Note,FA listing,SoundCloud
            track2,OST,note,https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek,https://soundcloud.com/dksslqj/muspelheim
            track1,OST,note,,https://soundcloud.com/dksslqj/muspelheim
            track3,OST,note,https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek,https://soundcloud.com/dksslqj/muspelheim
            track5,OST,note,https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek,
            track4,OST,note,,
            track6,TOURNAMENT_OFFICIAL,note,https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek,https://soundcloud.com/dksslqj/muspelheim
        ''').strip())

        article = ('wiki/osu!_originals/en.md', textwrap.dedent('''
            <!--
            markdown-generator9000 v1.0.0
            ---
            table:
                data: "meta/data/originals.csv"
                header:
                    - Icons
                    - Song
                    - Notes
                alignments:
                    - centre
                    - left
                    - left
                format:
                    - "<<icon link: FA listing>> <<icon link: SoundCloud>>"
                    - "[<<Track>>](<<FA listing>>)"
                    - "<<Note>>"
                filter: "<<Type>> is OST and <<Track>> has not track2"
                sort:
                    by: Track
                    order: ascending
            ---
            -->
        ''').strip())

        expected_table = textwrap.dedent('''
            | Icons | Song | Notes |
            | :-: | :-- | :-- |
            | [![](/wiki/shared/icon/soundcloud.png)](https://soundcloud.com/dksslqj/muspelheim) | track1 | note |
            | [![](/wiki/shared/icon/osu.png)](https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek) [![](/wiki/shared/icon/soundcloud.png)](https://soundcloud.com/dksslqj/muspelheim) | [track3](https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek) | note |
            |  | track4 | note |
            | [![](/wiki/shared/icon/osu.png)](https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek) | [track5](https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek) | note |
        ''').strip()

        expected_content = textwrap.dedent('''
            {}

            {}
        ''').strip().format(article[1], expected_table) \
            + extra[1] \
            + "\n" # trailing new line is enforced by remark and thus should be expected

        utils.create_files(root, (article[0], article[1] + ''.join(extra)), csv_file)

        exit_code = template_generator.main("--target", article[0])

        assert exit_code == 0

        with open(article[0], "r", encoding='utf-8') as fd:
            content = fd.read()

        print(f"extra: `{''.join(extra)}`")
        assert content == expected_content

    @pytest.mark.parametrize(
        "extra",
        [
            ('', ''),
            ('', '\n\n# content'),
            ('', '\n\n# content\n\nmore content'),
            ('\n\n## content (deleted)', '\n\n# content'),
            ('\n\n| existing table (deleted)', ''),
            ('\n\n| existing table (deleted)', '\n\n# content'),
            ('\n\n| existing table (deleted)', '\n\n# content\n\nmore content'),
            ('\n\n| existing table (deleted)\n\n## content', ''),
        ]
    )
    def test__generate_split_template_with_prefix(self, root, extra):
        csv_file = ('meta/data/originals.csv', textwrap.dedent('''
            Track,Type,Note,FA listing,SoundCloud
            track0,TOURNAMENT_OFFICIAL,note,https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek,https://soundcloud.com/dksslqj/muspelheim
            track2,OST,note,https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek,https://soundcloud.com/dksslqj/muspelheim
            track1,OST,note,,https://soundcloud.com/dksslqj/muspelheim
            track3,OST,note,https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek,https://soundcloud.com/dksslqj/muspelheim
            track5,OST,note,https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek,
            track4,OST,note,,
            track6,TOURNAMENT_COMMUNITY,note,https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek,https://soundcloud.com/dksslqj/muspelheim
        ''').strip())

        article = ('wiki/osu!_originals/en.md', textwrap.dedent('''
            # Tables

            <!--
            markdown-generator9000 v1.0.0
            ---
            table:
                data: "meta/data/originals.csv"
                header:
                    - Song
                alignments:
                    - left
                format:
                    - "<<Track>>"
                sort:
                    by: Track
                    order: ascending
                filter: "<<Type>> is not TOURNAMENT_COMMUNITY and <<Track>> has not track2"
                split:
                    by: Type
                    order: ascending
                    prefix_format: "## <<Type>>"
            ---
            -->
        ''').strip())

        expected_table = textwrap.dedent('''
            ## OST

            | Song |
            | :-- |
            | track1 |
            | track3 |
            | track4 |
            | track5 |

            ## TOURNAMENT_OFFICIAL

            | Song |
            | :-- |
            | track0 |
        ''').strip()

        expected_content = textwrap.dedent('''
            {}

            {}
        ''').strip().format(article[1], expected_table) \
            + extra[1] \
            + "\n" # trailing new line is enforced by remark and thus should be expected

        utils.create_files(root, (article[0], article[1] + ''.join(extra)), csv_file)

        exit_code = template_generator.main("--target", article[0])

        assert exit_code == 0

        with open(article[0], "r", encoding='utf-8') as fd:
            content = fd.read()

        print(f"extra: `{''.join(extra)}`")
        assert content == expected_content

    @pytest.mark.parametrize(
        "extra",
        [
            ('', ''),
            ('', '\n\n# content'),
            ('', '\n\n# content\n\nmore content'),
            ('\n\n## content (deleted)', '\n\n# content'),
            ('\n\n| existing table (deleted)', ''),
            ('\n\n| existing table (deleted)', '\n\n# content'),
            ('\n\n| existing table (deleted)', '\n\n# content\n\nmore content'),
            ('\n\n| existing table (deleted)\n\n## content', ''),
        ]
    )
    def test__generate_split_template_without_prefix(self, root, extra):
        csv_file = ('meta/data/originals.csv', textwrap.dedent('''
            Track,Type,Note,FA listing,SoundCloud
            track0,TOURNAMENT_OFFICIAL,note,https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek,https://soundcloud.com/dksslqj/muspelheim
            track2,OST,note,https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek,https://soundcloud.com/dksslqj/muspelheim
            track1,OST,note,,https://soundcloud.com/dksslqj/muspelheim
            track3,OST,note,https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek,https://soundcloud.com/dksslqj/muspelheim
            track5,OST,note,https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek,
            track4,OST,note,,
            track6,TOURNAMENT_COMMUNITY,note,https://osu.ppy.sh/beatmaps/artists/tracks?artist=James%20Landino&query=Hide%20and%20Seek,https://soundcloud.com/dksslqj/muspelheim
        ''').strip())

        article = ('wiki/osu!_originals/en.md', textwrap.dedent('''
            # Tables

            <!--
            markdown-generator9000 v1.0.0
            ---
            table:
                data: "meta/data/originals.csv"
                header:
                    - Song
                alignments:
                    - left
                format:
                    - "<<Track>>"
                sort:
                    by: Track
                    order: ascending
                filter: "<<Type>> is not TOURNAMENT_COMMUNITY and <<Track>> has not track2"
                split:
                    by: Type
                    order: ascending
            ---
            -->
        ''').strip())

        expected_table = textwrap.dedent('''
            | Song |
            | :-- |
            | track1 |
            | track3 |
            | track4 |
            | track5 |

            | Song |
            | :-- |
            | track0 |
        ''').strip()

        expected_content = textwrap.dedent('''
            {}

            {}
        ''').strip().format(article[1], expected_table) \
            + extra[1] \
            + "\n" # trailing new line is enforced by remark and thus should be expected

        utils.create_files(root, (article[0], article[1] + ''.join(extra)), csv_file)

        exit_code = template_generator.main("--target", article[0])

        assert exit_code == 0

        with open(article[0], "r", encoding='utf-8') as fd:
            content = fd.read()

        print(f"extra: `{''.join(extra)}`")
        assert content == expected_content
