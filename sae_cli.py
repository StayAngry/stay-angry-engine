"""Command Line Interface for the Visual Intelligence & Cinematic Effects Engine."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sae.creative.models import EditingBlueprint, PlatformFormat
from sae.database import DatabaseManager
from sae.effects.engine import CinematicEffectsEngine
from sae.effects.models import CreativeLookType
from sae.events import EventBus
from sae.media.manager import MediaAssetManager
from sae.render.engine import MediaProcessingEngine
from sae.resources import ResourceManager
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
        choices=["VERTICAL_SHORT", "HORIZONTAL_FULL", "SQUARE"],
        help="Target platform video aspect format",
    )
    process_parser.add_argument("--duration", "-d", type=float, default=15.0, help="Target duration in seconds")
    process_parser.add_argument("--output-dir", "-o", type=Path, default=Path("output"), help="Render output directory")

    # Command: verify
    verify_parser = subparsers.add_parser("verify", help="Verify integrity and resolution of a rendered file")
    verify_parser.add_argument("rendered_file", type=Path, help="Path to rendered media file")
    verify_parser.add_argument("--width", type=int, default=1080, help="Expected video width")
    verify_parser.add_argument("--height", type=int, default=1920, help="Expected video height")

    return parser


async def run_analyze(args: argparse.Namespace) -> int:
    media_path = args.media_path.resolve()
    if not media_path.exists():
        print(f"[ERROR] Asset not found at: {media_path}", file=sys.stderr)
        return 1

    print(f"[*] Analyzing asset: {media_path.name}...")
    db = DatabaseManager(Path("sae_workspace.db"))
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, cache_dir=Path("cache"))
    vision_engine = AdvancedVideoIntelligenceEngine(media_mgr)

    report = await vision_engine.analyze_asset(str(media_path))
    output_data = report.model_dump() if hasattr(report, "model_dump") else report.dict()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
        print(f"[+] Intelligence report saved to: {args.output}")
    else:
        print(json.dumps(output_data, indent=2))

    return 0


async def run_process(args: argparse.Namespace) -> int:
    media_path = args.media_path.resolve()
    if not media_path.exists():
        print(f"[ERROR] Asset not found at: {media_path}", file=sys.stderr)
        return 1

    args.output_dir.mkdir(parents=True, exist_ok=True)
    db = DatabaseManager(Path("sae_workspace.db"))
    bus = EventBus()
    media_mgr = MediaAssetManager(db, bus, cache_dir=Path("cache"))
    res_mgr = ResourceManager()

    format_mapping = {
        "VERTICAL_SHORT": (1080, 1920, PlatformFormat.VERTICAL_SHORT),
        "HORIZONTAL_FULL": (1920, 1080, PlatformFormat.HORIZONTAL_FULL if hasattr(PlatformFormat, "HORIZONTAL_FULL") else PlatformFormat.VERTICAL_SHORT),
        "SQUARE": (1080, 1080, PlatformFormat.VERTICAL_SHORT),
    }
    width, height, target_format = format_mapping.get(args.format, (1080, 1920, PlatformFormat.VERTICAL_SHORT))

    print(f"[*] Step 1/4: Analyzing visual intelligence for {media_path.name}...")
    vision_engine = AdvancedVideoIntelligenceEngine(media_mgr)
    report = await vision_engine.analyze_asset(str(media_path))

    print(f"[*] Step 2/4: Generating editing blueprint ({args.format} - {width}x{height})...")
    blueprint = EditingBlueprint(
        blueprint_id=f"bp_{media_path.stem}",
        title=args.title,
        format=target_format,
        width=width,
        height=height,
        fps=60.0,
        target_duration_sec=args.duration,
    )

    print(f"[*] Step 3/4: Applying creative look treatment ({args.look})...")
    effects_engine = CinematicEffectsEngine()
    treatment = effects_engine.generate_treatment(
        blueprint=blueprint,
        intelligence=report,
        look=CreativeLookType(args.look),
    )
    blueprint = effects_engine.apply_treatment(blueprint, treatment)

    print(f"[*] Step 4/4: Rendering media output via backend pipeline...")
    render_engine = MediaProcessingEngine(
        output_dir=args.output_dir,
        resource_manager=res_mgr,
    )
    rendered_file = await render_engine.render_blueprint(blueprint)

    print(f"[+] Render complete! Output generated at: {rendered_file}")
    return 0


async def run_verify(args: argparse.Namespace) -> int:
    from sae.render.verifier import RenderVerificationError, RenderVerifier

    rendered_path = args.rendered_file.resolve()
    verifier = RenderVerifier()

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


def main() -> None:
    parser = setup_parser()
    args = parser.parse_args()

    if args.command == "analyze":
        sys.exit(asyncio.run(run_analyze(args)))
    elif args.command == "process":
        sys.exit(asyncio.run(run_process(args)))
    elif args.command == "verify":
        sys.exit(asyncio.run(run_verify(args)))


if __name__ == "__main__":
    main()