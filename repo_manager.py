import httpx
import io
import shutil
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath
from uuid import uuid4

from context_builder import SKIP_DIRS, SKIP_EXTENSIONS

MAX_PATH_LEN = 200
MAX_REPO_SIZE_MB = 100


def parse_github_url(url: str) -> tuple[str, str]:
    parts = url.strip().rstrip("/").removesuffix(".git").split("/")
    if len(parts) < 2 or "github.com" not in url:
        raise ValueError(f"Invalid GitHub URL: {url}")
    return parts[-2], parts[-1]


async def get_repo_info(owner: str, name: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{name}",
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=15,
        )
        if resp.status_code == 404:
            raise ValueError(f"Repository not found: {owner}/{name}")
        if resp.status_code == 403:
            raise ValueError("GitHub API rate limit exceeded. Try again later.")
        resp.raise_for_status()
        data = resp.json()
        return {
            "default_branch": data.get("default_branch", "main"),
            # GitHub returns repo size in KB
            "size_kb": int(data.get("size", 0) or 0),
        }


def _should_skip(rel_path: str) -> bool:
    parts = PurePosixPath(rel_path).parts
    if any(p in SKIP_DIRS for p in parts):
        return True
    ext = PurePosixPath(rel_path).suffix.lower()
    if ext in SKIP_EXTENSIONS:
        return True
    return False


async def download_repo(repo_url: str) -> Path:
    owner, name = parse_github_url(repo_url)
    info = await get_repo_info(owner, name)

    size_mb = info["size_kb"] / 1024
    if size_mb > MAX_REPO_SIZE_MB:
        raise ValueError(
            f"Repository too large ({size_mb:.1f} MB). "
            f"Maximum supported size is {MAX_REPO_SIZE_MB} MB."
        )

    branch = info["default_branch"]
    zip_url = f"https://github.com/{owner}/{name}/archive/refs/heads/{branch}.zip"

    async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
        resp = await client.get(zip_url)
        resp.raise_for_status()

    base_dir = Path(tempfile.gettempdir()) / "gitarch"
    base_dir.mkdir(exist_ok=True)
    dest = base_dir / f"{name}_{uuid4().hex[:8]}"
    dest.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        root_prefix = zf.namelist()[0]
        for member in zf.namelist():
            rel_path = member[len(root_prefix):]
            if not rel_path:
                continue

            if _should_skip(rel_path):
                continue

            target = dest / rel_path
            if len(str(target)) > MAX_PATH_LEN:
                continue

            if member.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(member))

    return dest


def cleanup(repo_path: Path):
    if repo_path and repo_path.exists():
        shutil.rmtree(repo_path, ignore_errors=True)


def cleanup_orphan_dirs(max_age_seconds: int = 3600) -> int:
    """Remove temp repo directories older than max_age_seconds. Returns count removed."""
    base_dir = Path(tempfile.gettempdir()) / "gitarch"
    if not base_dir.exists():
        return 0
    cutoff = time.time() - max_age_seconds
    removed = 0
    for entry in base_dir.iterdir():
        try:
            if entry.is_dir() and entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry, ignore_errors=True)
                removed += 1
        except OSError:
            continue
    return removed
