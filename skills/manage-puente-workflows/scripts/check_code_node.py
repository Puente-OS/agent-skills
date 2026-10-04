#!/usr/bin/env python3
"""Check a workflow code node script before it is saved."""

from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import tokenize
from pathlib import Path

HEADLESS_BROWSER_NODE_ID = "core.headless_browser"
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"xox[abposr]-[A-Za-z0-9-]{10,}"),
    re.compile(r"password\s*=\s*[\"']", re.IGNORECASE),
)
BROWSER_PACKAGES = {"playwright", "requests", "bs4", "lxml"}
UNAVAILABLE_BROWSER_PACKAGES = {"psycopg2", "pandas", "numpy", "selenium"}


def stdout_prints(tree: ast.AST) -> int:
    count = 0
    for node in ast.walk(tree):
        is_print = (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        )
        if is_print and not any(keyword.arg == "file" for keyword in node.keywords):
            count += 1
    return count


def imported_modules(tree: ast.AST) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def has_references_in_code(source: str) -> bool:
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)
    return any(
        "{{" in token.string for token in tokens if token.type != tokenize.COMMENT
    )


def uses_playwright_context(source: str) -> bool:
    return "sync_playwright()" in source or "async_playwright()" in source


def check(source: str, node_id: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        tree = ast.parse(source)
    except SyntaxError as error:
        return [f"Syntax error on line {error.lineno}: {error.msg}"], []
    if stdout_prints(tree) > 1:
        warnings.append(
            "More than one print() writes to stdout. Print only the final JSON; "
            "send debugging output to stderr with file=sys.stderr."
        )
    if has_references_in_code(source):
        warnings.append(
            "The script contains {{ }}. Read other nodes through contexto[...] "
            "instead of references inside code."
        )
    if any(pattern.search(source) for pattern in SECRET_PATTERNS):
        errors.append(
            "The script looks like it contains a credential. Remove it before saving."
        )
    is_browser_node = node_id == HEADLESS_BROWSER_NODE_ID
    if is_browser_node:
        unavailable = imported_modules(tree) & UNAVAILABLE_BROWSER_PACKAGES
        if unavailable:
            warnings.append(
                "The headless browser template does not include: "
                + ", ".join(sorted(unavailable))
                + f". Available packages: {', '.join(sorted(BROWSER_PACKAGES))}."
            )
        if not uses_playwright_context(source):
            errors.append(
                "Open the browser with `with sync_playwright() as p:` or "
                "`async with async_playwright() as p:`."
            )
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path, help="File with the node script")
    parser.add_argument("--node-id", required=True, help="Catalog node_id")
    arguments = parser.parse_args()
    errors, warnings = check(
        arguments.script.read_text(encoding="utf-8"), arguments.node_id
    )
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
