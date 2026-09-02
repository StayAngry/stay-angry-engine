"""Command Line Interface for the Stay Angry Engine (SAE)."""

import argparse
import asyncio
import sys
from pathlib import Path

from sae.audio.engine import AudioIntelligenceEngine
from sae.creative.engine import CreativeEditingEngine
from sae.creative.models import CreativeStyleType, PlatformFormat
from sae.database import DatabaseManager
from sae.effects.engine import AdvancedCreativeEngine
from sae.effects.models import CreativeLookType
from sae.events import EventBus
from sae.integrations.engine import EditorIntegrationEngine
from sae.integrations.models import EditorType
from sae.media.manager import MediaAssetManager
from sae.render.backend import FFmpegMediaBackend
from sae.render.engine import MediaProcessingEngine
from sae.render.verifier import MediaOutputVerifier, RenderVerificationError
from sae.vision.engine import AdvancedVideoIntelligenceEngine


def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sae",
        description="Cinematic Video Intelligence & Autonomous Editing Engine CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Available subcommands")

    # Command: analyze
    analyze_parser = subparsers.add_parser("analyze", help="Run visual intelligence analysis on a media file")
    analyze_parser.add_argument("media_path", type=Path, help="Path to input video/media asset")
    analyze_parser.add_argument("--output", "-o", type=Path, default=None, help="Path to save output report JSON")

    # Command: process
    process_parser = subparsers.add_parser("process", help="Run end-to-end autonomous analysis, treatment, and render")
    process_parser.add_argument("media_path", type=Path, help="Path to input video file")
    process_parser.add_argument("--title", "-t", type=str, default="Cinematic Reel", help="Blueprint project title")
    process_parser.add_argument(
        "--look",
        "-l",
        type=str,
        default=CreativeLookType.DARK_CINEMATIC.value,
        choices=[look.value for look in CreativeLookType],
        help="Creative color grading preset",
    )
    process_parser.add_argument(
        "--format",
        "-f",
        type=str,
        default="VERTICAL_SHORT",
        choices=["VERTICAL_SHORT", "HORIZONTAL_STANDARD", "SQUARE"],
        help="Target platform video aspect format",
    )
    process_parser.add_argument("--duration", "-d", type=float, default=15.0, help="Target duration in seconds")
    process_parser.add_argument("--output-dir", "-o", type=Path, default=Path("output"), help="Render output directory")
    process_parser.add_argument("--auto-vision", action="store_true", help="Use multimodal vision intelligence for timeline cuts")
    process_parser.add_argument("--snap-beats", action="store_true", help="Snap vision cut boundaries to musical tempo transients")

    # Command: verify
    verify_parser = subparsers.add_parser("verify", help="Verify integrity and resolution of a rendered file")
    verify_parser.add_argument("rendered_file", type=Path, help="Path to rendered media file")
    verify_parser.add_argument("--width", type=int, default=1080, help="Expected video width")
    verify_parser.add_argument("--height", type=int, default=1920, help="Expected video height")

    # Command: export
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
) -> tuple[MediaAssetManager, CreativeEditingEngine, AdvancedCreativeEngine, EditorIntegrationEngine, AudioIntelligenceEngine]:
    base_dir = work_dir or Path(".sae_cache")
    base_dir.mkdir(parents=True, exist_ok=True)
    db = DatabaseManager(base_dir / "sae_cli.db")
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, base_dir / "media")
    audio = AudioIntelligenceEngine(media_mgr)
    creative = CreativeEditingEngine(media_mgr, audio_engine=audio)
    effects = AdvancedCreativeEngine()
    editor_engine = EditorIntegrationEngine(media_mgr, export_root or (base_dir / "projects"))
    return media_mgr, creative, effects, editor_engine, audio


async def run_analyze(args: argparse.Namespace) -> int:
    media_mgr, _, _, _, _ = get_core_services()
    vision = AdvancedVideoIntelligenceEngine(media_manager=media_mgr)
    print(f"[*] Analyzing media asset: {args.media_path.name}...")
    report = vision.analyze_asset(args.media_path.name)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        print(f"[+] Analysis report saved to {args.output}")
    else:
        print(report.model_dump_json(indent=2))
    return 0


async def run_process(args: argparse.Namespace) -> int:
    _, creative, effects, _, _ = get_core_services()
    backend = FFmpegMediaBackend(args.output_dir)
    render_engine = MediaProcessingEngine(workspace_root=args.output_dir, backend=backend)

    aspect_enum = getattr(PlatformFormat, args.format, PlatformFormat.VERTICAL_SHORT)
    look_enum = CreativeLookType(args.look)

    if args.auto_vision:
        print(f"[*] Ingesting multimodal vision intelligence for '{args.media_path.name}' (snap_beats={args.snap_beats})...")
        blueprint = creative.ingest_vision_intelligence(
            asset_id=args.media_path.name,
            target_duration=args.duration,
            format_type=aspect_enum,
            snap_to_beats=args.snap_beats,
        )
    else:
        print(f"[*] Generating editing blueprint for '{args.title}'...")
        blueprint = creative.generate_reel_blueprint(
            title=args.title,
            target_duration=args.duration,
            format_type=aspect_enum,
        )

    print(f"[*] Synthesizing creative effects treatment ({look_enum.value})...")
    treatment = effects.generate_treatment(blueprint=blueprint, look=look_enum)

    print("[*] Dispatching autonomous render job...")
    rendered_file = await render_engine.render_blueprint(blueprint=blueprint)
    print(f"[+] Render complete! Output generated at: {rendered_file}")
    return 0


async def run_verify(args: argparse.Namespace) -> int:
    rendered_path = args.rendered_file.resolve()
    verifier = MediaOutputVerifier()

    try:
        await verifier.verify_output(
            rendered_path,
            expected_width=args.width,
            expected_height=args.height,
            raise_on_error=True,
        )
        print(f"[+] Verification passed for: {rendered_path.name}")
        return 0
    except RenderVerificationError as e:
        print(f"[!] Verification failed: {e}", file=sys.stderr)
        return 1


async def run_export(args: argparse.Namespace) -> int:
    _, creative, effects, editor_engine, _ = get_core_services(export_root=args.output_dir)

    if args.auto_vision:
        print(f"[*] Generating blueprint with multimodal vision ingestion for '{args.asset_id}' (snap_beats={args.snap_beats})...")
        bp = creative.ingest_vision_intelligence(
            asset_id=args.asset_id,
            target_duration=args.duration,
            snap_to_beats=args.snap_beats,
        )
    else:
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

    if args.command == "analyze":
        sys.exit(asyncio.run(run_analyze(args)))
    elif args.command == "process":
        sys.exit(asyncio.run(run_process(args)))
    elif args.command == "verify":
        sys.exit(asyncio.run(run_verify(args)))
    elif args.command == "export":
        sys.exit(asyncio.run(run_export(args)))


if __name__ == "__main__":
    main()
