from __future__ import annotations

from typing import List

from .linter import DefaultLinter


def _ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def file_editor(file_path: str, start: int, end: int, content: str) -> None:
    """Replace the specified 1-based inclusive line range with content.

    Matches the minimal behavior expected by agentskills usage.
    """
    if not isinstance(start, int) or not isinstance(end, int):
        print("[file_editor] start and end must be integers")
        return
    if start < 1:
        start = 1
    if end < start:
        end = start

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            original = f.read()
    except Exception as exc:
        print(f"[file_editor] read error: {exc}")
        return

    if not original.endswith("\n"):
        original += "\n"

    lines: List[str] = original.splitlines(True)
    total = max(1, len(lines))
    start_idx = max(0, min(total - 1, start - 1))
    end_idx = max(0, min(total - 1, end - 1))

    replacement = _ensure_trailing_newline(content).splitlines(True)
    lines[start_idx : end_idx + 1] = replacement

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("".join(lines))
    except Exception as exc:
        print(f"[file_editor] write error: {exc}")
        return

    if file_path.endswith(".py"):
        linter = DefaultLinter()
        errors = linter.lint(file_path)
        if errors:
            error_text = "ERRORS:\n" + "\n".join(
                [f"{file_path}:{e.line}:{e.column}: {e.message}" for e in errors]
            )
            print('[Your proposed edit has introduced new syntax error(s). Please understand the errors and retry your edit command.]\n' + error_text)
            return

    print('[File updated (edited at line {line_number}). Please review the changes and make sure they are correct (correct indentation, no duplicate lines, etc). Edit the file again if necessary.]'.format(line_number=start))

