import textwrap
import types

import tests.conftest
import tests.utils as utils

from wikitools.template_generator import Alignment, SortOrder, Format, Filter
from wikitools.template_generator import FilterMode, FilterOperatorFunction, Tag
from wikitools.template_descriptor import load_template_descriptors

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
                filter:
                  include: "<<Type>> is OST"
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

        assert descriptor.line == 24

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

    def test__load_template_filter(self, root):
        article = ('wiki/osu!_originals/en.md', textwrap.dedent('''
            <!--
            markdown-generator9000 v1.0.0
            ---
            table:
                filter:
                  include: "<<Type>> is OST"
                  exclude:
                    - "<<Artist>> has cYsmix"
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

        assert isinstance(descriptor.filter, Filter)

        assert descriptor.filter.include_mode == FilterMode.AND
        assert descriptor.filter.exclude_mode == FilterMode.OR

        assert len(descriptor.filter.excludes) == 1

        assert isinstance(descriptor.filter.excludes[0], tuple)
        assert isinstance(descriptor.filter.excludes[0][0], types.LambdaType)
        assert descriptor.filter.excludes[0][0] == FilterOperatorFunction.HAS

        assert isinstance(descriptor.filter.excludes[0][1], Format)
        assert len(descriptor.filter.excludes[0][1]._format) == 1
        assert isinstance(descriptor.filter.excludes[0][1]._format[0], Tag)
        assert descriptor.filter.excludes[0][1]._format[0].columns == ["Artist"]
        assert descriptor.filter.excludes[0][1]._format[0].action is None

        assert len(descriptor.filter.includes) == 1

        assert isinstance(descriptor.filter.includes[0], tuple)
        assert isinstance(descriptor.filter.includes[0][0], types.LambdaType)
        assert descriptor.filter.includes[0][0] == FilterOperatorFunction.IS

        assert isinstance(descriptor.filter.includes[0][1], Format)
        assert len(descriptor.filter.includes[0][1]._format) == 1
        assert isinstance(descriptor.filter.includes[0][1]._format[0], Tag)
        assert descriptor.filter.includes[0][1]._format[0].columns == ["Type"]
        assert descriptor.filter.includes[0][1]._format[0].action is None
