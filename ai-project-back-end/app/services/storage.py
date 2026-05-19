from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import BinaryIO

_STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")  # "local" or "s3"
_LOCAL_ROOT = Path(
    os.getenv(
        "STORAGE_LOCAL_ROOT",
        str(Path(__file__).resolve().parents[2] / "var" / "storage"),
    )
)


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


async def store_file(*, content: bytes, namespace: str, filename: str) -> str:
    """Store a file and return a storage path/reference."""
    if _STORAGE_BACKEND == "s3":
        return await _store_s3(content=content, namespace=namespace, filename=filename)
    return await _store_local(content=content, namespace=namespace, filename=filename)


async def load_file(*, reference: str) -> bytes:
    """Load a file by its storage reference."""
    if _STORAGE_BACKEND == "s3":
        return await _load_s3(reference=reference)
    return await _load_local(reference=reference)


async def delete_file(*, reference: str) -> None:
    """Delete a file by its storage reference."""
    if _STORAGE_BACKEND == "s3":
        return await _delete_s3(reference=reference)
    return await _delete_local(reference=reference)


# ---------------------------------------------------------------------------
# Local filesystem backend
# ---------------------------------------------------------------------------


async def _store_local(*, content: bytes, namespace: str, filename: str) -> str:
    file_id = str(uuid.uuid4())[:8]
    ext = Path(filename).suffix
    rel_path = f"{namespace}/{file_id}{ext}"
    full_path = _LOCAL_ROOT / rel_path
    _ensure_dir(full_path)
    full_path.write_bytes(content)
    return f"local:{rel_path}"


async def _load_local(*, reference: str) -> bytes:
    if not reference.startswith("local:"):
        raise ValueError(f"Invalid local reference: {reference}")
    rel_path = reference[len("local:"):]
    full_path = _LOCAL_ROOT / rel_path
    if not full_path.exists():
        raise FileNotFoundError(f"File not found: {reference}")
    return full_path.read_bytes()


async def _delete_local(*, reference: str) -> None:
    if not reference.startswith("local:"):
        return
    rel_path = reference[len("local:"):]
    full_path = _LOCAL_ROOT / rel_path
    if full_path.exists():
        full_path.unlink()


# ---------------------------------------------------------------------------
# S3-compatible backend (stubs -- implement when boto3 is available)
# ---------------------------------------------------------------------------


async def _store_s3(*, content: bytes, namespace: str, filename: str) -> str:
    raise NotImplementedError(
        "S3 storage not configured. Set STORAGE_BACKEND=local or install boto3."
    )


async def _load_s3(*, reference: str) -> bytes:
    raise NotImplementedError("S3 storage not configured.")


async def _delete_s3(*, reference: str) -> None:
    raise NotImplementedError("S3 storage not configured.")
