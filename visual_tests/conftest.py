import collections
import typing


class VisualTestCase(collections.namedtuple('VisualTestCase', 'description function')):
    description: str
    function: typing.Callable


class VisualTest(collections.namedtuple('VisualTest', 'name description cases')):
    name: str
    description: str
    cases: typing.List[VisualTestCase]
