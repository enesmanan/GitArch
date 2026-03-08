import re
from pathlib import Path
from google.genai import types
from context_builder import read_file_safe, SKIP_DIRS, SKIP_EXTENSIONS


def get_tool_declarations() -> list:
    return [
        types.FunctionDeclaration(
            name="read_file",
            description="Read the content of a specific file in the repository",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "file_path": {
                        "type": "STRING",
                        "description": "Relative file path from repo root, e.g. 'src/main.py'",
                    }
                },
                "required": ["file_path"],
            },
        ),
        types.FunctionDeclaration(
            name="search_code",
            description="Search for a pattern (regex) across all files in the repository. Returns matching lines with file paths.",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "pattern": {
                        "type": "STRING",
                        "description": "Regex pattern to search for, e.g. 'import.*flask' or 'def main'",
                    }
                },
                "required": ["pattern"],
            },
        ),
        types.FunctionDeclaration(
            name="list_directory",
            description="List contents of a directory in the repository",
            parameters={
                "type": "OBJECT",
                "properties": {
                    "dir_path": {
                        "type": "STRING",
                        "description": "Relative directory path from repo root, e.g. 'src/' or '.'",
                    }
                },
                "required": ["dir_path"],
            },
        ),
    ]


class ToolExecutor:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def execute(self, name: str, args: dict) -> str:
        handlers = {
            "read_file": self._read_file,
            "search_code": self._search_code,
            "list_directory": self._list_directory,
        }
        handler = handlers.get(name)
        if not handler:
            return f"Unknown tool: {name}"
        try:
            return handler(**args)
        except Exception as e:
            return f"Error: {e}"

    def _read_file(self, file_path: str) -> str:
        target = self.repo_path / file_path
        if not target.exists():
            return f"File not found: {file_path}"
        if not target.is_file():
            return f"Not a file: {file_path}"
        content = read_file_safe(target)
        return content if content else "Could not read file (binary or too large)"

    def _search_code(self, pattern: str) -> str:
        results = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            return f"Invalid regex pattern: {pattern}"

        for path in self.repo_path.rglob("*"):
            if not path.is_file():
                continue
            if any(skip in path.parts for skip in SKIP_DIRS):
                continue
            if path.suffix in SKIP_EXTENSIONS:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for i, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    rel = str(path.relative_to(self.repo_path)).replace("\\", "/")
                    results.append(f"{rel}:{i}: {line.strip()}")
                    if len(results) >= 50:
                        return "\n".join(results) + "\n... (truncated at 50 results)"

        return "\n".join(results) if results else "No matches found"

    def _list_directory(self, dir_path: str) -> str:
        target = self.repo_path / dir_path
        if not target.exists():
            return f"Directory not found: {dir_path}"
        if not target.is_dir():
            return f"Not a directory: {dir_path}"

        items = []
        for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name)):
            if entry.name in SKIP_DIRS:
                continue
            suffix = "/" if entry.is_dir() else ""
            items.append(f"{entry.name}{suffix}")
        return "\n".join(items) if items else "(empty directory)"
