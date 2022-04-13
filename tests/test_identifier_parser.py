from wikitools import identifier_parser


class TestIdentifierParser:
    def test__plain_headings(self):
        for heading, identifier in (
            ('# Game modifiers', None),
            ('## Game modifiers', 'game-modifiers'),
            ('### Game modifiers', 'game-modifiers'),
            ('#### Game modifiers', 'game-modifiers'),
        ):
            assert identifier_parser.extract_identifier(heading) == identifier

    # this uses real-life examples
    def test__punctuation(self):
        for heading, identifier in (
            (
                "## I've forgotten my username and password!",
                "i've-forgotten-my-username-and-password!"
            ), (
                "## What is this 'Bancho authentication error' I keep receiving?",
                "what-is-this-'bancho-authentication-error'-i-keep-receiving?"
            ), (
                '## What is "restricted" mode, exactly?',
                'what-is-"restricted"-mode,-exactly?'
            ),
        ):
            assert identifier_parser.extract_identifier(heading) == identifier

    def test__figure(self):
        for heading, identifier in (
            ('### ![osu! icon](/wiki/shared/mode/osu.png) pippi', 'pippi'),
            ('### Mani ![osu!mania icon](/wiki/shared/mode/mania.png) Mari', 'mani-mari'),
            ('### osu! ![][osu!]', 'osu!'),
        ):
            assert identifier_parser.extract_identifier(heading) == identifier

    def test__link(self):
        for heading, identifier in (
            ('## [accounts@example.com](mailto:accounts@example.com)', 'accounts@example.com'),
            ('## I dare you, I [double dare you](/wiki/Say_what_again)', 'i-dare-you,-i-double-dare-you'),
            ('## A [b](/wiki/B) c d!', 'a-b-c-d!'),
            ('## A [wild](/wiki/B) l[ink](/wiki/Ink) appears ![abc](/img/abc.png)', 'a-wild-link-appears'),
        ):
            assert identifier_parser.extract_identifier(heading) == identifier

    def test__custom(self):
        for line, identifier in (
            ('osu! is a free-to-win game.', None),
            ('## How to play better {#get-good}', 'get-good'),
            ('## osu.ppy.sh {id=website}', 'website'),
            ('A regular line, but with an anchor. {id=tag}', 'tag'),
            ('{id=only-identifier-here}', 'only-identifier-here'),
            ('Now this is a story all about how my life got flipped. {#turned-upside-down}', 'turned-upside-down'),
        ):
            assert identifier_parser.extract_identifier(line) == identifier

    def test__unicode(self):
        for heading, identifier in (
            ('### Что случится, если я нарушу правила?', 'что-случится,-если-я-нарушу-правила?'),
            ('### 当我违反规定时会发生什么？', '当我违反规定时会发生什么？'),
            ('### Écran des résultats', 'écran-des-résultats'),
        ):
            assert identifier_parser.extract_identifier(heading) == identifier
