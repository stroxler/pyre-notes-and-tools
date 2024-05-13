from __future__ import annotations

import logging
import argparse
import ast
import glob
from pathlib import Path

logging.basicConfig()
logger = logging.getLogger(__name__)


class GlobalRebindFinder(ast.NodeVisitor):

    in_scope: dict[str, str]
    re_binds: dict[str, list[str]]


    def __init__(self) -> None:
        super().__init__()
        self.in_scope = {}
        self.re_binds = {}

    def add_name_to_scope(self, name: str, value: str) -> None:
        # Handle re-binds; for each one we track the full history of definitions.
        if name in self.in_scope:
            if name not in self.re_binds:
                self.re_binds[name] = [self.in_scope[name]]
            self.re_binds[name].append(value)
        # Add the name to the current scope.
        self.in_scope[name] = value

    def visit_Import(self, node: ast.Import) -> None:
        for name in node.names:
            defined_name = name.name if name.asname is None else name.asname
            value = name.name
            self.add_name_to_scope(defined_name, "(import) " + value)
        return None

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for name in node.names:
            defined_name = name.name if name.asname is None else name.asname
            value = (
                name.name
                if node.module is None else
                ".".join([node.module, name.name])
            )
            self.add_name_to_scope(defined_name, "(import from) " + value)
        return None

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                name = target.id
                value = ast.dump(node.value)
                self.add_name_to_scope(name, value)
        return None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.add_name_to_scope(node.name, f"class::{node.name}")
        # We do not call `generic_visit`, so we do not visit anything nested inside a class body.
        return None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.add_name_to_scope(node.name, f"function::{node.name}")
        # We do not call `generic_visit`, so we do not visit anything nested inside a function body.
        return None
    

def re_binds_in_source(source_path: Path) -> dict[str, list[str]]:
    logger.info(f"Checking source path {source_path}")
    with open(source_path, "r") as f:
        source_ast = ast.parse(f.read())
    global_rebind_finder = GlobalRebindFinder()
    global_rebind_finder.visit(source_ast)
    return global_rebind_finder.re_binds


def re_binds_in_directory(directory: Path) -> dict[str, dict[str, list[str]]]:
    python_modules_and_stubs = [
        relative_path for relative_path in (
            *glob.glob(
                pathname="**/*.py",
                root_dir=directory,
                recursive=True,
            ),
            *glob.glob(
                pathname="**/*.pyi",
                root_dir=directory,
                recursive=True,
            ),
        )
        if not ("setup.py" in relative_path or "test" in relative_path)
    ]
    return {
        f"{directory}/{source_path}": re_binds_in_source(Path(directory) / Path(source_path))
        for source_path in python_modules_and_stubs
    }


def main(directory: Path) -> None:
    directory_re_binds = re_binds_in_directory(directory)
    if len(directory_re_binds) == 0:
        print(f"(No global re-binds found in {directory})")
    for source_path, source_re_binds in directory_re_binds.items():
        if len(source_re_binds) > 0:
            print(f"---\n{source_path}")
            for name, values in source_re_binds.items():
                print(f"  {name}")
                for value in values:
                    print(f"    {value}")


if __name__  == "__main__":
    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "source_directory",
        help=(
            "Directory to check for global re-binds."
        ),
        type=str,
    )
    args = parser.parse_args()
    main(directory=Path(args.source_directory))
