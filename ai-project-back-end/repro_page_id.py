import json
from pathlib import Path
from typing import Any

def _find_manifest_page(manifest: dict[str, Any], page_id: str) -> dict[str, Any]:
    pages = manifest.get("pages")
    if not isinstance(pages, list):
        print("manifest_pages_invalid")
        return None
    for page in pages:
        if isinstance(page, dict) and str(page.get("id") or "").strip() == page_id:
            return page
    print("page_not_found")
    return None

def test():
    manifest_path = Path("d:/ai-project/docs/figma/manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    print(f"Testing 'sample-login-page': {True if _find_manifest_page(manifest, 'sample-login-page') else False}")
    print(f"Testing 'sample-login-page ': {True if _find_manifest_page(manifest, 'sample-login-page ') else False}")
    print(f"Testing 'sample_login_page': {True if _find_manifest_page(manifest, 'sample_login_page') else False}")

if __name__ == "__main__":
    test()
