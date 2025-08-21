from __future__ import annotations

import os
from typing import List


def explore_tree_structure(path: str = ".", max_depth: int = 3) -> None:
    try:
        for root, dirs, files in os.walk(path):
            depth = root[len(path):].count(os.sep)
            if depth > max_depth:
                dirs[:] = []
                continue
            indent = "  " * depth
            print(f"{indent}{os.path.basename(root)}/")
            for f in files:
                print(f"{indent}  {f}")
    except Exception as e:
        print(f"[explore_tree_structure] error: {e}")


def get_entity_contents(path: str, start_line: int | None = None, end_line: int | None = None) -> None:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
        s = (start_line or 1) - 1
        e = (end_line or len(lines))
        selected = lines[s:e]
        print("\n".join(selected))
    except Exception as e:
        print(f"[get_entity_contents] error: {e}")


def search_code_snippets(term: str, root: str = ".") -> None:
    matches: List[str] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.startswith('.'):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    for lineno, line in enumerate(f, 1):
                        if term in line:
                            matches.append(f"{fp}:{lineno}:{line.strip()}")
            except Exception:
                continue
    if not matches:
        print(f"[search_code_snippets] No matches for '{term}' under {root}")
    else:
        print("\n".join(matches))

