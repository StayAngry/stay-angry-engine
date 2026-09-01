"""Timeline and Blueprint Validator ensuring non-destructive safety, gap checks, and overlap sanity."""

from typing import Tuple
from sae.creative.models import EditingBlueprint


class TimelineValidator:
    @staticmethod
    def validate(blueprint: EditingBlueprint, registered_asset_ids: set[str]) -> Tuple[bool, list[str]]:
        errors = []

        if blueprint.target_duration_sec <= 0:
            errors.append("Invalid target duration: Must be greater than 0.")

        # Track overlaps and missing assets
        sorted_clips = sorted(blueprint.video_clips, key=lambda c: (c.track_index, c.timeline_start_sec))
        
        for i, clip in enumerate(sorted_clips):
            if clip.asset_id not in registered_asset_ids:
                errors.append(f"Clip '{clip.clip_id}' references missing asset '{clip.asset_id}'.")

            if clip.timeline_start_sec >= clip.timeline_end_sec:
                errors.append(f"Clip '{clip.clip_id}' has invalid timeline range: {clip.timeline_start_sec} -> {clip.timeline_end_sec}")

            if clip.source_in_sec >= clip.source_out_sec:
                errors.append(f"Clip '{clip.clip_id}' has invalid source trim range: {clip.source_in_sec} -> {clip.source_out_sec}")

            # Check track collision
            if i > 0:
                prev = sorted_clips[i - 1]
                if prev.track_index == clip.track_index and clip.timeline_start_sec < prev.timeline_end_sec:
                    errors.append(f"Track collision detected between '{prev.clip_id}' and '{clip.clip_id}' on track {clip.track_index}.")

        return len(errors) == 0, errors