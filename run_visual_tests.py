#!/usr/bin/env python3

"""
Runs visual tests

Use the up and down arrow keys to cycle between tests, and
use the left and right arrow keys to cycle between test cases.

Press Esc to quit.
"""

import argparse
from pynput.keyboard import Key, Listener  # type: ignore
import sys
from traceback import format_exc


from tests.conftest import get_visual_tests
from wikitools import console


def run_all_tests(test_list):
    for test_index, test in enumerate(test_list):
        for case_index, test_case in enumerate(test.cases):
            run_test(test_list, test_index, case_index)


def run_test(test_list, test_index, case_index):
    test = test_list[test_index]
    print(f"({test_index + 1}/{len(test_list)})", console.red(test.name), "-", test.description)
    test_case = test.cases[case_index]
    print()
    print(f"- ({case_index + 1}/{len(test.cases)})", console.blue(test_case.description))
    print()
    try:
        test_case.function()
    except SystemExit as e:
        print()
        print(f"Program exited with {console.red(e.code) if e.code != 0 else console.green(e.code)}")
    except Exception:
        print()
        print(console.red("Exception raised:"), format_exc())


test_index = 0
case_index = 0


def key_handler(key, test_list):
    global test_index
    global case_index

    if key == Key.up:
        test_index -= 1
    elif key == Key.down:
        test_index += 1
    elif key == Key.left:
        case_index -= 1
    elif key == Key.right:
        case_index += 1

    if test_index < 0:
        test_index = len(test_list) - 1
    elif test_index >= len(test_list):
        test_index = 0
    if case_index < 0:
        case_index = len(test_list[test_index].cases) - 1
    elif case_index >= len(test_list[test_index].cases):
        case_index = 0

    elif key == Key.esc:
        print()
        return False

    print("\033c", end="")
    run_test(test_list, test_index, case_index)
    print()
    print("Navigate with arrow keys. Press Esc to quit.")


def run_interactively(test_list):
    print("\033c", end="")
    run_test(test_list, 0, 0)
    print()
    print("Navigate with arrow keys. Press Esc to quit.")
    with Listener(on_press=lambda key: key_handler(key, test_list)) as listener:  # type: ignore
        listener.join()


def parse_args(args):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-a", "--all", action='store_true', help="run all tests sequentially (non-interactively)")
    return parser.parse_args(args)


def main():
    args = parse_args(sys.argv[1:])

    test_list = get_visual_tests()
    if not test_list:
        print(console.red("Error:"), "no tests found")
        sys.exit(1)

    if args.all:
        run_all_tests(test_list)
    else:
        run_interactively(test_list)


if __name__ == "__main__":
    main()
