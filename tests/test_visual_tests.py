from tests.conftest import get_visual_tests
from tests.conftest import run_visual_test


tests = get_visual_tests()


class TestVisualTests:
    pass


def make_method(test_index, case_index):
    def method(self):
        global tests
        nonlocal test_index
        nonlocal case_index
        run_visual_test(tests, test_index, case_index)
    return method


for test in tests:
    for test_index, test in enumerate(tests):
        test_slug = test.name.lower().replace(" ", "_")
        for case_index, test_case in enumerate(test.cases):
            setattr(TestVisualTests, f"test_visual__{test_slug}__{test_case.name}", make_method(test_index, case_index))
