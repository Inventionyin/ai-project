from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from fastapi import HTTPException


class PostmanCloudClient:
    def __init__(
        self,
        *,
        api_key: str,
        workspace_id: str | None = None,
        base_url: str = "https://api.getpostman.com",
        timeout: int = 30,
    ) -> None:
        self._api_key = str(api_key or "").strip()
        self._workspace_id = str(workspace_id or "").strip()
        self._base_url = str(base_url or "https://api.getpostman.com").rstrip("/")
        self._timeout = max(int(timeout or 30), 1)
        if not self._api_key:
            raise HTTPException(status_code=400, detail="postman_api_key_required")

    def list_collections(self) -> list[dict[str, str | None]]:
        query = ""
        if self._workspace_id:
            query = "?" + urlencode({"workspace": self._workspace_id})
        payload = self._request_json(f"/collections{query}")
        rows = payload.get("collections") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            return []
        out: list[dict[str, str | None]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            uid = str(row.get("uid") or row.get("id") or "").strip()
            name = str(row.get("name") or "").strip()
            if not uid or not name:
                continue
            out.append(
                {
                    "id": str(row.get("id") or "").strip() or None,
                    "uid": uid,
                    "name": name,
                    "updatedAt": str(row.get("updatedAt") or "").strip() or None,
                }
            )
        return out

    def get_collection(self, collection_uid: str) -> dict[str, Any]:
        uid = str(collection_uid or "").strip()
        if not uid:
            raise HTTPException(status_code=400, detail="postman_collection_uid_required")
        payload = self._request_json(f"/collections/{quote(uid, safe='')}")
        collection = payload.get("collection") if isinstance(payload, dict) else None
        if not isinstance(collection, dict):
            raise HTTPException(status_code=502, detail="postman_collection_invalid_response")
        return collection

    def _request_json(self, path: str) -> dict[str, Any]:
        request = Request(
            f"{self._base_url}{path}",
            headers={
                "X-Api-Key": self._api_key,
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = "postman_api_error"
            try:
                body = exc.read().decode("utf-8")
                parsed = json.loads(body or "{}")
                if isinstance(parsed, dict):
                    detail = str(parsed.get("error", {}).get("message") or parsed.get("message") or detail)
            except Exception:
                pass
            raise HTTPException(status_code=502, detail=detail) from exc
        except URLError as exc:
            raise HTTPException(status_code=502, detail="postman_api_unreachable") from exc
        try:
            parsed = json.loads(raw or "{}")
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=502, detail="postman_api_invalid_json") from exc
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=502, detail="postman_api_invalid_response")
        return parsed
