"""Cinematic Video Intelligence & Autonomous Editing Engine Command Line Interface."""

import argparse
import asyncio
from pathlib import Path
import sys

from sae.audio.engine import AudioIntelligenceEngine
from sae.audio.loudness_engine import AudioLoudnessEngine
from sae.audio.loudness_models import LoudnessTargetStandard
from sae.creative.engine import CreativeEditingEngine
from sae.creative.models import CreativeStyleType, PlatformFormat
from sae.database import DatabaseManager
from sae.effects.color import CinematicColorEngine
from sae.effects.engine import AdvancedCreativeEngine
from sae.effects.models import CreativeLookType
from sae.effects.typography_engine import KineticTypographyEngine
from sae.events import EventBus
from sae.integrations.engine import EditorIntegrationEngine
from sae.integrations.models import EditorType
from sae.media.manager import MediaAssetManager
from sae.orchestrator.engine import DirectorPipeline
from sae.render.backend import FFmpegMediaBackend, MockMediaBackend
from sae.render.engine import MediaProcessingEngine
from sae.render.verifier import MediaOutputVerifier, RenderVerificationError
from sae.vision.engine import AdvancedVideoIntelligenceEngine


def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sae",
        description="Cinematic Video Intelligence & Autonomous Editing Engine CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available subcommands")

    # Subcommand: direct
    direct_parser = subparsers.add_parser("direct", help="Execute end-to-end autonomous synthesis via DirectorPipeline")
    direct_parser.add_argument("--title", "-t", type=str, default="Autonomous Action Reel", help="Reel title")
    direct_parser.add_argument("--duration", "-d", type=float, default=6.0, help="Target duration in seconds")
    direct_parser.add_argument(
        "--style",
        type=str,
        default=CreativeStyleType.DARK_MANHWA.value,
        choices=[s.value for s in CreativeStyleType],
        help="Creative visual style",
    )
    direct_parser.add_argument(
        "--format",
        type=str,
        default=PlatformFormat.VERTICAL_SHORT.value,
        choices=[f.value for f in PlatformFormat],
        help="Platform canvas format",
    )
    direct_parser.add_argument("--transcript", nargs="*", default=["AWAKEN", "SHADOW", "MONARCH"], help="Kinetic subtitle words")
    direct_parser.add_argument("--mock-render", action="store_true", help="Use lightweight mock rendering backend")

    # Subcommand: analyze
    analyze_parser = subparsers.add_parser("analyze", help="Run visual intelligence analysis on a media file")
    analyze_parser.add_argument("media_path", type=Path, help="Path to input video/media asset")
    analyze_parser.add_argument("--output", "-o", type=Path, default=None, help="Path to save output report JSON")

    # Subcommand: process
    process_parser = subparsers.add_parser("process", help="Run autonomous analysis, treatment, and render")
    process_parser.add_argument("media_path", type=Path, help="Path to input video file")
    process_parser.add_argument("--title", "-t", type=str, default="Cinematic Reel", help="Blueprint project title")
    process_parser.add_argument(
        "--look",
        "-l",
        type=str,
        default=CreativeLookType.DARK_CINEMATIC.value,
        choices=[look.value for look in CreativeLookType],
        help="Creative look preset",
    )
    process_parser.add_argument("--duration", "-d", type=float, default=15.0, help="Target duration in seconds")
    process_parser.add_argument("--aspect", "-a", type=str, default="9:16", choices=["9:16", "16:9", "1:1"], help="Canvas aspect ratio")
    process_parser.add_argument("--snap-beats", action="store_true", help="Snap cut timings to audio transients")

    # Subcommand: verify
    verify_parser = subparsers.add_parser("verify", help="Verify media file compliance against standard requirements")
    verify_parser.add_argument("rendered_file", type=Path, help="Path to rendered media file to verify")
    verify_parser.add_argument("--width", type=int, default=1080, help="Expected video width")
    verify_parser.add_argument("--height", type=int, default=1920, help="Expected video height")

    # Subcommand: export
    export_parser = subparsers.add_parser("export", help="Export blueprint to NLE project file (DaVinci Resolve EDL or Premiere FCPXML)")
    export_parser.add_argument(
        "--target",
        "-t",
        type=str,
        default="davinci",
        choices=["davinci", "premiere"],
        help="Target NLE editor format",
    )
    export_parser.add_argument("--title", type=str, default="Cinematic Project", help="Timeline project title")
    export_parser.add_argument("--duration", "-d", type=float, default=15.0, help="Target duration in seconds")
    export_parser.add_argument("--output-dir", "-o", type=Path, default=Path("output"), help="Export directory")
    export_parser.add_argument("--dry-run", action="store_true", help="Generate manifest without writing to disk")
    export_parser.add_argument("--asset-id", type=str, default="default_asset_001.mp4", help="Asset ID for vision extraction")
    export_parser.add_argument("--auto-vision", action="store_true", help="Use multimodal vision intelligence for timeline cuts")
    export_parser.add_argument("--snap-beats", action="store_true", help="Snap vision cut boundaries to musical tempo transients")

    return parser


def get_core_services(
    export_root: Path | None = None,
    work_dir: Path | None = None,
    mock_render: bool = False,
):
    base_dir = work_dir or Path(".sae_cache")
    base_dir.mkdir(parents=True, exist_ok=True)
    db = DatabaseManager(base_dir / "sae_cli.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, base_dir / "media")
    audio = AudioIntelligenceEngine(media_mgr)
    creative = CreativeEditingEngine(media_mgr, audio_engine=audio)
    color = CinematicColorEngine()
    effects = AdvancedCreativeEngine(color)
    editor_engine = EditorIntegrationEngine(media_mgr, export_root or (base_dir / "projects"))
    vision = AdvancedVideoIntelligenceEngine(media_mgr)
    loudness = AudioLoudnessEngine(media_mgr)
    typography = KineticTypographyEngine(media_mgr, output_dir=base_dir / "subtitles")

    backend = MockMediaBackend(output_dir=Path("output")) if mock_render else FFmpegMediaBackend(output_dir=Path("output"))
    render = MediaProcessingEngine(workspace_root=base_dir, backend=backend)

    director = DirectorPipeline(
        media_manager=media_mgr,
        creative_engine=creative,
        vision_engine=vision,
        audio_engine=audio,
        loudness_engine=loudness,
        effects_engine=effects,
        typography_engine=typography,
        render_engine=render,
    )

    return {
        "media_mgr": media_mgr,
        "creative": creative,
        "effects": effects,
        "editor": editor_engine,
        "audio": audio,
        "render": render,
        "director": director,
    }


async def run_direct(args: argparse.Namespace) -> int:
    print(f"[*] Initializing Autonomous DirectorPipeline for '{args.title}'...")
    services = get_core_services(mock_render=args.mock_render)
    director = services["director"]

    style_enum = CreativeStyleType(args.style)
    format_enum = PlatformFormat(args.format)

    manifest = await director.produce_reel(
        title=args.title,
        target_duration=args.duration,
        style=style_enum,
        format_type=format_enum,
        loudness_standard=LoudnessTargetStandard.REELS_TIKTOK_SHORT,
        sample_transcript=args.transcript,
    )

    print("[+] Direct synthesis complete!")
    print(f"    - Pipeline ID: {manifest.pipeline_id}")
    print(f"    - Rendered Output: {manifest.rendered_video_path}")
    print(f"    - Kinetic Subtitles: {manifest.subtitle_track_path}")
    print(f"    - Clips Assembled: {manifest.total_clips}")
    print(f"    - Loudness Calibrated: {manifest.loudness_calibrated}")
    return 0


async def run_analyze(args: argparse.Namespace) -> int:
    services = get_core_services()
    media_mgr = services["media_mgr"]
    print(f"[*] Analyzing media asset: {args.media_path.name}")
    asset = media_mgr.register_asset(args.media_path)
    print(f"[+] Ingestion complete for asset: {asset.asset_id}")
    return 0


async def run_process(args: argparse.Namespace) -> int:
    services = get_core_services()
    creative = services["creative"]
    effects = services["effects"]
    render_engine = services["render"]

    aspect_enum = PlatformFormat.VERTICAL_SHORT if args.aspect == "9:16" else PlatformFormat.HORIZONTAL_STANDARD
    look_enum = CreativeLookType(args.look)

    blueprint = creative.generate_reel_blueprint(
        title=args.title,
        target_duration=args.duration,
        format_type=aspect_enum,
    )
    effects.generate_treatment(blueprint=blueprint, look=look_enum)
    rendered_file = await render_engine.render_blueprint(blueprint=blueprint)
    print(f"[+] Render complete! Output: {rendered_file}")
    return 0


async def run_verify(args: argparse.Namespace) -> int:
    verifier = MediaOutputVerifier()
    try:
        await verifier.verify_output(args.rendered_file.resolve(), expected_width=args.width, expected_height=args.height, raise_on_error=True)
        print(f"[+] Verification passed for: {args.rendered_file.name}")
        return 0
    except RenderVerificationError as e:
        print(f"[-] Verification failed: {e}")
        return 1


async def run_export(args: argparse.Namespace) -> int:
    services = get_core_services(export_root=args.output_dir)
    creative = services["creative"]
    effects = services["effects"]
    editor_engine = services["editor"]

    bp = creative.generate_reel_blueprint(title=args.title, target_duration=args.duration)
    treatment = effects.generate_treatment(bp)
    editor_type = EditorType.DAVINCI_RESOLVE if args.target == "davinci" else EditorType.PREMIERE_PRO

    manifest, out_path = editor_engine.export_to_editor(
        blueprint=bp,
        treatment=treatment,
        editor_type=editor_type,
        dry_run=args.dry_run,
    )
    if args.dry_run or out_path is None:
        print(f"[+] Dry run export successful for manifest ID: {manifest.manifest_id}")
    else:
        print(f"[+] Project successfully exported to: {out_path}")
    return 0


def main() -> None:
    parser = setup_parser()
    args = parser.parse_args()

    commands = {
        "direct": run_direct,
        "analyze": run_analyze,
        "process": run_process,
        "verify": run_verify,
        "export": run_export,
    }

    handler = commands.get(args.command)
    if handler:
        sys.exit(asyncio.run(handler(args)))


if __name__ == "__main__":
    main()
