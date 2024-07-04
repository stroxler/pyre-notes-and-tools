#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess


def main(
    pattern: str,
    replacement: str | None,
) -> None:
    if replacement is None:
        subprocess.check_call(["rg", pattern])
    else:
        files = (
            subprocess.check_output(["rg", pattern, "-l"])
            .decode("utf-8")
            .strip()
            .split("\n")
        )
        print(
            f"Replacing {pattern} with {replacement} in these files:\n\t" +
            "\n\t".join(files)
        )
        subprocess.check_call(
            ["sed", "-i", "", f"s/{pattern}/{replacement}/g", *files]
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "pattern",
        help=(
            "The ripgrep pattern to search for; used by default for sed as well."
        "--pattern",
        ),
        type=str,
    )
    parser.add_argument(
        "-r",
        "--replacement",
        help=(
            "What to replace the pattern with. If not specified, we'll just "
            "show the raw `rg` output, which makes it easier to look and then "
            "replace."
        ),
        type=str,
    )
    args = parser.parse_args()
    main(
        args.pattern,
        args.replacement,
    )

"""
rg ParameterVariadicTypeVariable -l | \
  xargs sed -i '' 's/ParameterVariadicTypeVariable/FromParamSpec/g'rg ParameterVariadicTypeVariable -l | xargs sed -i '' 's/ParameterVariadicTypeVariable/FromParamSpec/g'
"""
