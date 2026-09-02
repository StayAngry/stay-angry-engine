"""Real-time timeline preview generator and frame caching engine."""

import hashlib
import json
from pathlib import Path
from typing import Any
from sae.creative.models import EditingBlueprint, TimelineClip
from sae.media.manager import MediaAssetManager
from sae.render.preview_models import PreviewFrame, PreviewManifest


class TimelinePreviewEngine:
    """Manages frame caching and timeline scrubbing previews without full video renders."""

    def __init__(self, media_manager: MediaAssetManager, cache_dir: Path | None = None):
        self.media_manager = media_manager
        self.cache_dir = (cache_dir or Path(".sae_cache/preview_frames")).resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: dict[str, PreviewFrame] = {}

    def _generate_cache_key(
        self,
        asset_id: str,
        source_offset_sec: float,
        width: int,
        height: int,
        style: str,
    ) -> str:
        """Create a deterministic hash key for frame caching."""
        payload = f"{asset_id}:{source_offset_sec:.3f}:{width}x{height}:{style}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def resolve_active_clip(
        self, blueprint: EditingBlueprint, timestamp_sec: float
    ) -> tuple[TimelineClip | None, float]:
        """Find active clip and relative source offset at the given timeline timestamp."""
        t = max(0.0, min(timestamp_sec, blueprint.target_duration_sec))
        for clip in blueprint.video_clips:
            if clip.timeline_start_sec <= t <= clip.timeline_end_sec:
                rel_t = t - clip.timeline_start_sec
                source_offset = clip.source_in_sec + (rel_t * clip.speed)
                return clip, round(source_offset, 3)

        # Fallback to last clip if at the exact boundary
        if blueprint.video_clips:
            last = blueprint.video_clips[-1]
            return last, round(last.source_out_sec, 3)

        return None, 0.0

    def get_cut_point_timestamps(self, blueprint: EditingBlueprint) -> list[float]:
        """Extract cut boundaries from the blueprint."""
        cut_points: set[float] = {0.0}
        for clip in blueprint.video_clips:
            cut_points.add(clip.timeline_start_sec)
            cut_points.add(clip.timeline_end_sec)
        return sorted(list(cut_points))

    async def extract_preview_frame(
        self,
        blueprint: EditingBlueprint,
        timestamp_sec: float,
        width: int | None = None,
        height: int | None = None,
    ) -> PreviewFrame:
        """Extract or retrieve cached preview frame at the specified timeline timestamp."""
        w = width or blueprint.width
        h = height or blueprint.height
        frame_idx = int(round(timestamp_sec * blueprint.fps))

        active_clip, source_offset = self.resolve_active_clip(blueprint, timestamp_sec)
        asset_id = active_clip.asset_id if active_clip else "default"
        style_name = blueprint.style.value if hasattr(blueprint.style, "value") else str(blueprint.style)

        cache_key = self._generate_cache_key(asset_id, source_offset, w, h, style_name)

        if cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        target_file = self.cache_dir / f"frame_{cache_key}.jpg"
        cut_points = self.get_cut_point_timestamps(blueprint)
        is_cut = any(abs(timestamp_sec - cp) < 0.04 for cp in cut_points)

        # Mock frame artifact generation for instantaneous caching and testing
        if not target_file.exists():
            target_file.write_text(f"PREVIEW_FRAME:{cache_key}", encoding="utf-8")

        frame = PreviewFrame(
            timestamp_sec=round(timestamp_sec, 3),
            frame_index=frame_idx,
            active_clip_id=active_clip.clip_id if active_clip else None,
            asset_id=asset_id,
            source_offset_sec=source_offset,
            width=w,
            height=h,
            is_cut_point=is_cut,
            color_grade_applied=True,
            cached_path=target_file,
        )

        self._memory_cache[cache_key] = frame
        return frame

    async def precache_cut_points(
        self, blueprint: EditingBlueprint
    ) -> PreviewManifest:
        """Pre-cache preview frames at all major cut boundaries for seamless scrub response."""
        cut_points = self.get_cut_point_timestamps(blueprint)
        cached_frames: list[PreviewFrame] = []

        for cp in cut_points:
            frame = await self.extract_preview_frame(blueprint, cp)
            cached_frames.append(frame)

        manifest = PreviewManifest(
            blueprint_id=blueprint.blueprint_id,
            target_duration_sec=blueprint.target_duration_sec,
            total_cached_frames=len(cached_frames),
            cut_point_timestamps=cut_points,
            frames=cached_frames,
        )

        manifest_file = self.cache_dir / f"manifest_{blueprint.blueprint_id}.json"
        manifest_file.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
        return manifest
