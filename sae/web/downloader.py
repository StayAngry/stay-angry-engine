"""Quarantine Download Manager with defensive file extension validation and size boundaries."""

import hashlib
import re
from pathlib import Path
from typing import Any
import httpx
from sae.web.gateway import GatewaySecurityError, InternetGateway


class QuarantineDownloader:
    BLOCKED_EXTENSIONS = {
        ".exe", ".dll", ".bat", ".cmd", ".ps1", ".vbs", ".msi", ".com", ".scr", ".sh", ".jar"
    }

    ALLOWED_MEDIA_EXTENSIONS = {
        ".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov", ".mp3", ".wav", ".json", ".txt", ".csv"
    }

    def __init__(self, quarantine_dir: Path, gateway: InternetGateway | None = None, max_download_bytes: int = 25 * 1024 * 1024):
        self.quarantine_dir = quarantine_dir.resolve()
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.gateway = gateway or InternetGateway()
        self.max_download_bytes = max_download_bytes

    def sanitize_filename(self, filename: str) -> str:
        clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
        return clean.strip("._") or "downloaded_asset"

    async def download_to_quarantine(self, url: str, suggested_name: str | None = None) -> dict[str, Any]:
        self.gateway.validate_url(url)
        
        parsed_name = Path(url.split("?")[0]).name
        raw_name = suggested_name or parsed_name or "downloaded_file.bin"
        filename = self.sanitize_filename(raw_name)
        target_ext = Path(filename).suffix.lower()

        if target_ext in self.BLOCKED_EXTENSIONS:
            raise GatewaySecurityError(f"Security Block: Disallowed file extension '{target_ext}'.")

        target_path = self.quarantine_dir / filename
        counter = 1
        while target_path.exists():
            target_path = self.quarantine_dir / f"{target_path.stem}_{counter}{target_path.suffix}"
            counter += 1

        sha256 = hashlib.sha256()
        total_bytes = 0

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                async with client.stream("GET", url) as response:
                    self.gateway.validate_url(str(response.url))
                    if response.status_code >= 400:
                        raise GatewaySecurityError(f"Download failed with status {response.status_code}")

                    with open(target_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            total_bytes += len(chunk)
                            if total_bytes > self.max_download_bytes:
                                target_path.unlink(missing_ok=True)
                                raise GatewaySecurityError(f"Download exceeded size limit of {self.max_download_bytes} bytes.")
                            sha256.update(chunk)
                            f.write(chunk)
            except Exception as e:
                target_path.unlink(missing_ok=True)
                raise GatewaySecurityError(f"Download error: {e}")

        return {
            "quarantine_path": str(target_path),
            "size_bytes": total_bytes,
            "sha256": sha256.hexdigest(),
            "status": "QUARANTINED_UNTRUSTED"
        }