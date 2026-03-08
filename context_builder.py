from pathlib import Path

SKIP_DIRS = {
    ".git", "node_modules", "venv", ".venv", "__pycache__",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".egg-info", ".eggs", "env", ".env",
    "__snapshots__", "e2e", "e2e_playwright", "coverage",
    ".next", ".nuxt", ".cache", ".parcel-cache",
    "vendor", "third_party", "assets", "static",
}

SKIP_EXTENSIONS = {
    ".lock", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot", ".mp3", ".mp4", ".zip",
    ".tar", ".gz", ".bz2", ".exe", ".dll", ".so", ".dylib",
    ".pyc", ".pyo", ".class", ".o", ".a",
}

PRIORITY_FILENAMES = [
    "main.py", "app.py", "index.py", "server.py", "manage.py",
    "index.ts", "index.js", "app.ts", "app.js", "server.ts", "server.js",
    "main.go", "main.rs", "main.java",
]

PRIORITY_PATTERNS = [
    "docker-compose", "Dockerfile", "Makefile",
    "pyproject.toml", "setup.py", "setup.cfg", "package.json",
    "requirements", "Cargo.toml", "go.mod",
    "routes", "api", "models", "schema", "config", "settings",
]

MAX_FILE_CHARS = 15_000
MAX_TOTAL_CHARS = 300_000


def get_file_tree(repo_path: Path) -> str:
    lines = []
    _walk_tree(repo_path, repo_path, "", lines)
    return "\n".join(lines)


def _walk_tree(root: Path, current: Path, prefix: str, lines: list):
    entries = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    dirs = [e for e in entries if e.is_dir() and e.name not in SKIP_DIRS]
    files = [e for e in entries if e.is_file() and e.suffix not in SKIP_EXTENSIONS]
    items = dirs + files

    for i, item in enumerate(items):
        is_last = i == len(items) - 1
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}")
        if item.is_dir():
            extension = "    " if is_last else "│   "
            _walk_tree(root, item, prefix + extension, lines)


def read_file_safe(path: Path, max_chars: int = MAX_FILE_CHARS) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if len(text) > max_chars:
            return text[:max_chars] + f"\n... [truncated, {len(text)} chars total]"
        return text
    except Exception:
        return None


def _file_priority(path: Path) -> int:
    name = path.name.lower()
    if name == "readme.md" or name == "readme.rst" or name == "readme.txt":
        return 0
    if name in [p.lower() for p in PRIORITY_FILENAMES]:
        return 1
    for pat in PRIORITY_PATTERNS[:3]:
        if pat.lower() in name.lower():
            return 2
    for pat in PRIORITY_PATTERNS[3:]:
        if pat.lower() in name.lower():
            return 3
    if path.suffix in {".py", ".ts", ".js", ".go", ".rs", ".java"}:
        return 4
    return 5


def _collect_files(repo_path: Path) -> list[Path]:
    files = []
    for p in repo_path.rglob("*"):
        if p.is_file() and not any(skip in p.parts for skip in SKIP_DIRS) and p.suffix not in SKIP_EXTENSIONS:
            files.append(p)
    files.sort(key=lambda p: (_file_priority(p), len(str(p)), p.name.lower()))
    return files


def build_context(repo_path: Path) -> dict:
    tree = get_file_tree(repo_path)

    readme = ""
    for name in ["README.md", "README.rst", "README.txt", "README"]:
        readme_path = repo_path / name
        if readme_path.exists():
            readme = read_file_safe(readme_path) or ""
            break

    files = _collect_files(repo_path)
    file_contents = {}
    total_chars = 0

    for f in files:
        rel = str(f.relative_to(repo_path)).replace("\\", "/")
        content = read_file_safe(f)
        if content is None:
            continue
        if total_chars + len(content) > MAX_TOTAL_CHARS:
            break
        file_contents[rel] = content
        total_chars += len(content)

    return {
        "tree": tree,
        "readme": readme,
        "files": file_contents,
        "repo_path": repo_path,
    }
