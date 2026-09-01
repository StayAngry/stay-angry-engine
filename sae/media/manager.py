"""Central Media Asset Manager for scanning approved directories, asset querying, and tagging."""

import json
import uuid
from pathlib import Path
from typing import Any
from sae.database import DatabaseManager
from sae.events import EventBus
from sae.media.extractors import MetadataExtractor
from sae.media.models import CreativeAttributes, MediaAsset, MediaStyle, MediaType


class MediaAssetManager:
    def __init__(self, db: DatabaseManager, event_bus: EventBus, cache_dir: Path | None = None):
        self.db = db
        self.event_bus = event_bus
        self.cache_dir = cache_dir or Path("sae_workspace/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _init_tables(self) -> None:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS media_assets (
                    asset_id TEXT PRIMARY KEY,
                    file_path TEXT UNIQUE,
                    filename TEXT,
                    media_type TEXT,
                    file_size_bytes INTEGER,
                    content_hash TEXT,
                    width INTEGER,
                    height INTEGER,
                    duration_sec REAL,
                    fps REAL,
                    tags TEXT,
                    user_rating INTEGER,
                    creative_json TEXT,
                    created_at TEXT
                )
            """)
            conn.commit()

    def scan_directory(self, directory: Path) -> list[MediaAsset]:
        discovered: list[MediaAsset] = []
        if not directory.exists() or not directory.is_dir():
            return discovered

        for file_path in directory.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                asset = self.register_file(file_path)
                if asset:
                    discovered.append(asset)
        return discovered

    def register_file(self, path: Path) -> MediaAsset | None:
        media_type = MetadataExtractor.detect_type(path)
        if media_type == MediaType.UNKNOWN:
            return None

        content_hash = MetadataExtractor.calculate_hash(path)
        file_size = path.stat().st_size
        asset_id = f"asset_{uuid.uuid4().hex[:8]}"

        w, h, duration, fps = None, None, None, None
        scenes = []
        audio_data = None

        if media_type == MediaType.IMAGE:
            w, h = MetadataExtractor.extract_image_dimensions(path)
        elif media_type == MediaType.VIDEO:
            w, h = (1920, 1080)
            duration = 12.0
            fps = 24.0
            scenes = MetadataExtractor.detect_video_scenes(duration)
        elif media_type == MediaType.AUDIO:
            audio_data = MetadataExtractor.extract_audio_info(path)
            duration = audio_data.duration_sec

        # Tag heuristics based on filename
        tags = [media_type.value.lower()]
        name_lower = path.stem.lower()
        if any(k in name_lower for k in ("anime", "manhwa", "amv", "edit")):
            tags.extend(["anime", "cinematic"])

        creative = CreativeAttributes(
            style=MediaStyle.ANIME if "anime" in tags else MediaStyle.UNKNOWN,
            energy="HIGH" if "fight" in name_lower else "MEDIUM"
        )

        asset = MediaAsset(
            asset_id=asset_id,
            file_path=str(path.resolve()),
            filename=path.name,
            media_type=media_type,
            file_size_bytes=file_size,
            content_hash=content_hash,
            width=w,
            height=h,
            duration_sec=duration,
            fps=fps,
            tags=tags,
            scenes=scenes,
            audio_data=audio_data,
            creative=creative
        )

        self._save_asset_to_db(asset)
        return asset

    def _save_asset_to_db(self, asset: MediaAsset) -> None:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO media_assets (
                    asset_id, file_path, filename, media_type, file_size_bytes,
                    content_hash, width, height, duration_sec, fps, tags,
                    user_rating, creative_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                asset.asset_id,
                asset.file_path,
                asset.filename,
                asset.media_type.value,
                asset.file_size_bytes,
                asset.content_hash,
                asset.width,
                asset.height,
                asset.duration_sec,
                asset.fps,
                json.dumps(asset.tags),
                asset.user_rating,
                json.dumps(asset.creative.model_dump()),
                asset.created_at
            ))
            conn.commit()

    def search_assets(self, query: str) -> list[MediaAsset]:
        terms = [t.lower() for t in query.split()]
        all_assets = self.list_assets()
        matched = []
        for a in all_assets:
            score = 0
            if any(term in a.filename.lower() for term in terms):
                score += 2
            if any(term in [t.lower() for t in a.tags] for term in terms):
                score += 3
            if score > 0:
                matched.append((score, a))
        matched.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in matched]

    def list_assets(self) -> list[MediaAsset]:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM media_assets")
            rows = cursor.fetchall()
            assets = []
            for r in rows:
                creative_dict = json.loads(r["creative_json"]) if r["creative_json"] else {}
                assets.append(
                    MediaAsset(
                        asset_id=r["asset_id"],
                        file_path=r["file_path"],
                        filename=r["filename"],
                        media_type=MediaType(r["media_type"]),
                        file_size_bytes=r["file_size_bytes"],
                        content_hash=r["content_hash"],
                        width=r["width"],
                        height=r["height"],
                        duration_sec=r["duration_sec"],
                        fps=r["fps"],
                        tags=json.loads(r["tags"]) if r["tags"] else [],
                        user_rating=r["user_rating"],
                        creative=CreativeAttributes(**creative_dict),
                        created_at=r["created_at"]
                    )
                )
            return assets

    def tag_asset(self, asset_id: str, new_tags: list[str]) -> bool:
        for a in self.list_assets():
            if a.asset_id == asset_id:
                combined = list(set(a.tags + new_tags))
                a.tags = combined
                self._save_asset_to_db(a)
                return True
        return False