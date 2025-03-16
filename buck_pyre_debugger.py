# This is the beginning of a tool to inspect buck logs in a way
# that will make it easy to run pyre / pyrefly as a buck build
# using type checking macros.
#
# This only works internally, but nothing about the setup is secret
# and I don't have anything usable enough to check in, so I'm just
# dumping in my scratch repo for now.
#
# For anyone wondering how this works, we basically use BXL to ask
# buck for all the python files in a given python library or binary,
# and pass that information to the type checker via a json dump.
#
# This works great and lets us re-use a ton of buck infrastructure,
# but it's hard sometimes to print-debug the setup, and I've been
# playing around with the idea of building a script that can tease
# apart what buck is doing under the hood so that I could replay
# it easily in a debug setting.
#
# This scriptlet is a step in that direction
import subprocess
import sys
from pathlib import Path


def get_owning_target(filename: str) -> str:
    return subprocess.check_output(
        ["buck", "uquery", f"owner({filename})"],
        text=True,
    ).strip()


def get_type_check_json(target: str, root: str) -> Path:
    type_checking_target = target + "-type-checking"
    # We don't care whether type checking succeeds or not
    _ = subprocess.check_call(
        ["buck", "build", type_checking_target],
        text=True,
    )
    out = subprocess.check_output(["buck", "log", "what-ran"], text=True)
    type_check_config_path = next(
        part
        for part in out.split(" ")
        if part.startswith("buck-out") and part.endswith("type_check_config.json")
    )
    if type_check_config_path is None:
        raise RuntimeError("Could not find type_check_config.json")
    return Path(root) / type_check_config_path


def main():
    filename = sys.argv[1]
    root = subprocess.check_output(["hg", "root"], text=True).strip()
    owning_target = get_owning_target(filename)
    json_path = get_type_check_json(owning_target, root)
    print("\nType check json path:\n")
    print(json_path)
