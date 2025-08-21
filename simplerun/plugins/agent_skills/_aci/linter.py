from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class LintResult:
    line: int
    column: int
    message: str


class DefaultLinter:
    """Minimal Python syntax linter using built-in compile."""

    def lint(self, file_path: str) -> List[LintResult]:
        if not file_path.endswith(".py"):
            return []
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()
            compile(source, file_path, "exec")
            return []
        except SyntaxError as e:
            line = e.lineno or 1
            col = (e.offset or 1) if isinstance(e.offset, int) else 1
            msg = e.msg or "syntax error"
            return [LintResult(line=line, column=col, message=msg)]

