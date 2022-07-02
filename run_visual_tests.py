#!/usr/bin/env python3

"""
Runs visual tests

Use the up and down arrow keys to cycle between tests, and
use the left and right arrow keys to cycle between test cases.

Press Esc to quit.
"""

import argparse
import importlib
import pkgutil
from pynput.keyboard import Key, Listener # type: ignore
import sys


import visual_tests
from wikitools import console


def get_tests():
    return [
        importlib.import_module(module).test for module in
        (
            module for _, module, _ in pkgutil.walk_packages(
                path=visual_tests.__path__,
                prefix=visual_tests.__name__ + '.',
                onerror=lambda _: None
            )
        )
        if "conftest" not in module
    ]


def run_all_tests(tests):
    for test_number, test in enumerate(tests, start=1):
        print(f"({test_number}/{len(tests)})", console.red(test.name), "-", test.description)
        for case_number, test_case in enumerate(test.cases, start=1):
            print()
            print(f"- ({case_number}/{len(test.cases)})", console.blue(test_case.description))
            print()
            try:
                test_case.function()
            except SystemExit as e:
                print()
                print(f"Program exited with {console.red(e.code) if e.code != 0 else console.green(e.code)}")
            except Exception as e:
                print()
                print(console.red("Exception raised:"), e)


def run_test(tests, test_index, case_index):
    print("\033c", end="")
    test = tests[test_index]
    print(f"({test_index + 1}/{len(tests)})", console.red(test.name), "-", test.description)
    test_case = test.cases[case_index]
    print()
    print(f"- ({case_index + 1}/{len(test.cases)})", console.blue(test_case.description))
    print()
    try:
        test_case.function()
    except SystemExit as e:
        print()
        print(f"Program exited with {console.red(e.code) if e.code != 0 else console.green(e.code)}")
    except Exception as e:
        print()
        print(console.red("Exception raised:"), e)


test_index = 0
case_index = 0


def key_handler(key, tests):
    global test_index
    global case_index

    if key == Key.up:
        test_index -= 1
        if test_index < 0:
            test_index = len(tests) - 1
    elif key == Key.down:
        test_index += 1
        if test_index >= len(tests):
            test_index = 0

    elif key == Key.left:
        case_index -= 1
        if case_index < 0:
            case_index = len(tests[test_index].cases) - 1
    elif key == Key.right:
        case_index += 1
        if case_index >= len(tests[test_index].cases):
            case_index = 0

    elif key == Key.esc:
        print()
        return False

    run_test(tests, test_index, case_index)


def run_interactively(tests):
    run_test(tests, 0, 0)
    with Listener(on_press=lambda key: key_handler(key, tests)) as listener: # type: ignore
        listener.join()



def parse_args(args):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-a", "--all", action='store_true', help="run all tests sequentially (non-interactively)")
    return parser.parse_args(args)


def main():
    args = parse_args(sys.argv[1:])

    tests = get_tests()
    if not tests:
        print(console.red("Error:"), "no tests found")
        sys.exit(1)

    if args.all:
        run_all_tests(tests)
    else:
        run_interactively(tests)


if __name__ == "__main__":
    main()
