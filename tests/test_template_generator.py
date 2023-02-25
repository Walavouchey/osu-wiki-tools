import textwrap

import tests.conftest
import tests.utils as utils

from wikitools.table_generator import load_template_descriptors, Alignment, SortOrder, Format, Filter

class TestTableGenerator:
    def test__load_template_descriptor(self, root):
        article = ('wiki/osu!_originals/en.md', textwrap.dedent('''
            <!--
            markdown-generator9000 v1.0.0
            ---
            table:
                data: "meta/data/originals.csv"
                header:
                    - Links
                    - Song
                    - Notes
                alignments:
                    - centre
                    - left
                    - left
                format:
                    - "<<icon link: FA listing>> <<icon link: SoundCloud>> <<icon link: YouTube>> <<icon link: Spotify>> <<icon link: Bandcamp>>"
                    - "<<Track>>"
                    - "<<Note>>"
                filter: "<<Type>> is 'OST'"
                sort:
                    by: Song
                    order: ascending
            ---
            -->
        ''').strip())

        utils.create_files(root, article)

        with open(article[0], "r", encoding='utf-8') as fd:
            content = fd.read()
            print(content)

        descriptors = load_template_descriptors(article[0])

        assert len(descriptors) == 1

        descriptor = descriptors[0]

        assert descriptor.line == 23

        assert descriptor.data == 'meta/data/originals.csv'

        assert descriptor.header == ['Links', 'Song', 'Notes']

        assert descriptor.alignments == [
                Alignment.CENTRE,
                Alignment.LEFT,
                Alignment.LEFT,
        ]

        assert len(descriptor.formats) == 3

        assert all(isinstance(f, Format) for f in descriptor.formats)

        assert isinstance(descriptor.filter, Filter)

        assert descriptor.sort_by == 'Song'

        assert descriptor.sort_order == SortOrder.ASCENDING
