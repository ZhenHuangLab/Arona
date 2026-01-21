"""
File serving endpoints.

Motivation
----------
Assistant responses (and parsed Markdown from `rag_storage/parsed_output`) often contain
image references such as:

- Relative: `images/<hash>.jpg` (relative to the parsed markdown file)
- Repo-relative: `rag_storage/parsed_output/.../images/<hash>.jpg`
- Absolute filesystem paths produced during processing

Browsers cannot resolve these local paths directly. This router exposes a safe,
read-only HTTP endpoint for images stored under the configured `upload_dir` and
`working_dir`.
"""

from __future__ import annotations

from functools import lru_cache
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import FileResponse


logger = logging.getLogger(__name__)
router = APIRouter()

# Keep this strictly to common raster formats. Avoid SVG to reduce XSS surface.
_ALLOWED_IMAGE_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _normalize_requested_path(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="path is required",
        )
    if "\x00" in value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid path",
        )

    # Common cases where the model includes quoting.
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        value = value[1:-1].strip()

    # Allow file:// URIs by converting to plain filesystem path.
    if value.lower().startswith("file://"):
        value = value[7:]

    return value


def _get_storage_roots(request: Request) -> tuple[Path, Path]:
    config = getattr(request.app.state, "config", None)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="backend config not initialized",
        )

    upload_root = Path(getattr(config, "upload_dir", "./uploads")).resolve()
    working_root = Path(getattr(config, "working_dir", "./rag_storage")).resolve()
    return upload_root, working_root


@lru_cache(maxsize=4096)
def _find_unique_parsed_image_path(*, filename: str, working_root: str) -> Optional[str]:
    """
    Best-effort resolver for markdown-relative `images/<hash>.<ext>` references.

    Parsed markdown files store images under:
      <working_dir>/parsed_output/**/images/<filename>
    but assistant messages often only include `images/<filename>`.
    Since filenames are content-hashes, they are expected to be globally unique.
    """
    search_root = Path(working_root) / "parsed_output"
    if not search_root.exists():
        return None

    best: Optional[Path] = None
    matches = 0
    for candidate in search_root.rglob(filename):
        # Limit to the typical images directories to avoid being a general file oracle.
        if "images" not in candidate.parts:
            continue
        if not candidate.is_file():
            continue
        if candidate.suffix.lower() not in _ALLOWED_IMAGE_SUFFIXES:
            continue

        matches += 1
        resolved = candidate.resolve()
        if best is None or str(resolved) < str(best):
            best = resolved

    if best is None:
        return None
    if matches > 1:
        logger.debug(
            "Multiple matches for parsed image %r under %s; using %s",
            filename,
            search_root,
            best,
        )
    return str(best)


def _resolve_image_path(
    *, requested: str, upload_root: Path, working_root: Path
) -> Optional[Path]:
    # Treat common web-style absolute paths as repo/storage-relative rather than
    # absolute filesystem paths (e.g. "/uploads/foo.png", "/images/bar.jpg").
    normalized = requested
    if normalized.startswith("/"):
        parts = Path(normalized).parts
        if len(parts) >= 2:
            top = parts[1]
            if top in {upload_root.name, working_root.name, "images"}:
                normalized = normalized.lstrip("/")

    candidate = Path(normalized)

    # If relative, try resolving against known roots first.
    if not candidate.is_absolute():
        for root in (working_root, upload_root):
            resolved = (root / candidate).resolve()
            if resolved.exists() and resolved.is_file() and (
                _is_relative_to(resolved, working_root) or _is_relative_to(resolved, upload_root)
            ):
                return resolved

    # Try as-is (absolute or repo-relative path that already includes working_root/upload_root).
    try:
        resolved = candidate.resolve()
    except Exception:  # noqa: BLE001
        return None

    if resolved.exists() and resolved.is_file() and (
        _is_relative_to(resolved, working_root) or _is_relative_to(resolved, upload_root)
    ):
        return resolved

    # Fallback: handle `images/<filename>` by searching under parsed_output/**/images/.
    suffix = candidate.suffix.lower()
    if suffix in _ALLOWED_IMAGE_SUFFIXES:
        found = _find_unique_parsed_image_path(
            filename=candidate.name, working_root=str(working_root)
        )
        if found:
            resolved_found = Path(found).resolve()
            if resolved_found.exists() and resolved_found.is_file() and _is_relative_to(
                resolved_found, working_root
            ):
                return resolved_found

    return None


@router.get("/files")
async def get_file(
    request: Request,
    path: str = Query(..., description="Image path (absolute or relative)"),
) -> FileResponse:
    """
    Serve an image stored under `upload_dir` or `working_dir`.

    Notes:
    - This endpoint is intentionally limited to common raster image formats.
    - Path traversal is prevented by restricting resolution to configured roots.
    """
    requested = _normalize_requested_path(path)
    upload_root, working_root = _get_storage_roots(request)

    resolved = _resolve_image_path(
        requested=requested, upload_root=upload_root, working_root=working_root
    )
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="file not found",
        )

    if resolved.suffix.lower() not in _ALLOWED_IMAGE_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"unsupported file type: {resolved.suffix}",
        )

    # Cache aggressively: parsed images are content-addressed and query images are timestamped.
    headers = {"Cache-Control": "public, max-age=3600"}
    return FileResponse(path=str(resolved), headers=headers)
