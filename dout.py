#!/usr/bin/python3
# (Use a python3 I'm certain isn't rosetta for now... if you use
#  an i386 python3 in an arm mac you'll have problems!)
"""
# dout: the dune ounit test runner.

This tool is my attempt to make a simple wrapper around dune + ounit
testing that is more ergonomic.

In the initial version the wrapper is very simple with only the easiest
wins that really improve turnaround times in the shell:
- Specify the test file path as `.ml` rather than `.exe`
- Single-letter flags to list test or specify a test case
- Allow filtering `-list-test` output by matching a test suite name
- Allow any partial match of test case name, not just prefix match.
  - In many cases this is minor since you can just list and copy/paste
  - But "line=<number>" works (and is always unique) which means it's
    now possible to skip the list test step!

There are a lot more things I think might be worth adding though. In
a rough (decreasing) order of importance, some ideas are:
  - Add `make test` support, which should not expose output directly
    but instead dump most of it to disk and only expose the useful bits.
    *Ideally* it would also dump directly the commands to isolate failing
    tests.
  - Guessing the meaning of output lines and colorizing them; especially
    to distinguish log output vs test framework output
  - Infer line ranges so you could specify any line in a test
  - Filtering standard error to cut out compiler warnings (this is mostly
    but not entirely superseded by just making sure important information
    is printed *after* the line noise).
  - Regex matches on test cases and/or the ability to match multiple cases
    when running isolated tests. So far I've not really wanted this.

"""
from __future__ import annotations

import argparse
import subprocess
import os
import typing

from pathlib import Path


def dune_env() -> typing.Mapping[str, str]:
    """
    Set up an enviornment forcing 1 shard for OUNIT.

    NOTE: it might be nice to replace this (except for `make test` where
    I think only an environment flag works) with instead using the
    "-shards" option in the command.
    """
    env = os.environ.copy()
    env["OUNIT_SHARDS"] = "1"
    return env


def get_exe_test_file(test_file: Path) -> Path:
    return test_file.with_suffix(".exe")


def dune_exec_command(test_file: Path) -> list[str]:
    return [
        "dune", "exec", str(get_exe_test_file(test_file)),
    ]


def dune_exec_subcommand(test_file: Path, subcommand: list[str]) -> list[str]:
    return [
        *dune_exec_command(test_file),
        "--",
        *subcommand,
    ]


def run_all_tests(test_file) -> None:
    subprocess.check_call(
        dune_exec_command(test_file),
        env=dune_env(),
    )


def get_test_names(test_file) -> str:
    output = subprocess.check_output(
        dune_exec_subcommand(test_file, ["-list-test"]),
        env=dune_env(),
        encoding="utf-8"
    )
    return output


def find_matching_test_names(
    list_test_out: str,
    test_case: str,
) -> list[str]:
    return [
        test_name
        for test_name in list_test_out.strip().split()
        if test_case in test_name
    ]


def run_list_tests(test_file, test_case: str | None) -> None:
    list_test_out = get_test_names(test_file)
    if test_case is None:
        print(list_test_out)
    else:
        for test_name in find_matching_test_names(
            list_test_out,
            test_case,
        ):
            print(test_name)


def run_test_case(test_file, test_case: str) -> None:
    matching_tests = find_matching_test_names(
        get_test_names(test_file),
        test_case,
    )
    if len(matching_tests) == 0:
        raise ValueError(f"Did not find test matching {test_case}")
    if len(matching_tests) > 1:
        raise ValueError(
            f"Too many tests matched {test_case}: "
            f"{matching_tests}"
        )
    matching_test = matching_tests[0]
    output = subprocess.check_call(
        dune_exec_subcommand(test_file, ["-only-test", matching_test]),
        env=dune_env(),
    )


def main(
    test_file: Path,
    list_tests: bool,
    test_case: str | None,
) -> None:
    if list_tests:
        run_list_tests(test_file, test_case)
    elif test_case is not None:
        run_test_case(test_file, test_case)
    else:
        run_all_tests(test_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "test_file",
        help=(
            "Specify a test file. "
            "Dune expects .exe filenames so it can run them; `dout` will automatically "
            "change the suffix which lets you use .ml files for nicer autocomplete."
        ),
        type=str,
    )
    parser.add_argument(
        "-l",
        "--list-tests",
        help=(
            "List the tests in this module."
        ),
        action="store_true",
    )
    parser.add_argument(
        "-t",
        "--test-case",
        help=(
            "Specify an individual test case. `dout` will use a simple contains match. "
            "If listing tests, we'll filter the output to lines that match this. "
        ),
        type=str,
    )
    args = parser.parse_args()
    main(
        test_file=Path(args.test_file),
        list_tests=args.list_tests,
        test_case=args.test_case,
    )