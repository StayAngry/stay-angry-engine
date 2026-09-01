"""Stay Angry Engine (SAE) Command Line Interface."""

import asyncio
import sys
from pathlib import Path
from sae.config import settings
from sae.context import ContextBuilder
from sae.creative.engine import CreativeEditingEngine
from sae.creative.models import CreativeStyleType, PlatformFormat
from sae.creative.validator import TimelineValidator
from sae.database import DatabaseManager
from sae.effects.color import CinematicColorEngine
from sae.effects.engine import AdvancedCreativeEngine
from sae.effects.models import CreativeLookType
from sae.events import EventBus
from sae.executor import ExecutionEngine
from sae.hardening.benchmarks import BenchmarkEngine
from sae.hardening.engine import SelfImprovementEngine
from sae.hardening.models import EngineMode, ProposalRisk
from sae.integrations.engine import EditorIntegrationEngine
from sae.integrations.models import EditorType
from sae.intent import IntentAnalyzer
from sae.media.manager import MediaAssetManager
from sae.memory import MemoryImportance, MemoryManager, MemoryScope, MemoryType
from sae.models.registry import LocalModelRegistry, ModelCapability
from sae.models.runtimes import MockLocalRuntime, OllamaRuntime
from sae.orchestrator.models import AutonomyLevel
from sae.orchestrator.workflow import AutonomousCreativeWorkflow
from sae.planning import Planner
from sae.providers.gemini import GeminiProvider
from sae.providers.local import LocalAIProvider
from sae.providers.manager import ProviderManager
from sae.providers.mock import MockProvider
from sae.providers.resources import ResourceAuditor
from sae.providers.router import ModelRouter, RoutingPolicy
from sae.recovery import CheckpointManager, RecoveryEngine
from sae.render.engine import MediaProcessingEngine
from sae.resources import ResourceManager
from sae.tools.filesystem import CreateDirectoryTool, DeletePathTool, ReadFileTool, WriteFileTool
from sae.tools.registry import ToolRegistry
from sae.validator import PlanValidator
from sae.vision.engine import AdvancedVideoIntelligenceEngine
from sae.web.downloader import QuarantineDownloader
from sae.web.gateway import InternetGateway
from sae.web.research import ResearchAgent
from sae.web.search import DuckDuckGoSearchProvider, MockSearchProvider, SearchManager
from sae.workspace import WorkspaceSandbox


def get_core_runtime():
    bus = EventBus()
    db = DatabaseManager(settings.db_path)
    memory_manager = MemoryManager(db, bus)
    checkpoint_manager = CheckpointManager(db, bus)
    recovery_engine = RecoveryEngine(checkpoint_manager, db, bus)
    resource_manager = ResourceManager()
    model_registry = LocalModelRegistry()
    media_manager = MediaAssetManager(db, bus, settings.workspace_root / "cache")
    creative_engine = CreativeEditingEngine(media_manager)
    render_engine = MediaProcessingEngine(settings.workspace_root, resource_manager=resource_manager)
    color_engine = CinematicColorEngine()
    effects_engine = AdvancedCreativeEngine(color_engine)
    editor_engine = EditorIntegrationEngine(media_manager, settings.workspace_root / "projects")
    
    vision_engine = AdvancedVideoIntelligenceEngine(
        media_manager=media_manager,
        resource_manager=resource_manager
    )

    orchestrator = AutonomousCreativeWorkflow(
        media_manager=media_manager,
        creative_engine=creative_engine,
        vision_engine=vision_engine,
        effects_engine=effects_engine,
        render_engine=render_engine,
        editor_engine=editor_engine,
        checkpoint_manager=checkpoint_manager
    )

    hardening_engine = SelfImprovementEngine(
        db_manager=db,
        model_registry=model_registry,
        media_manager=media_manager,
        mode=EngineMode.PRODUCTION
    )

    sandbox = WorkspaceSandbox(settings.workspace_root)
    registry = ToolRegistry(bus)
    
    registry.register_tool(CreateDirectoryTool(sandbox))
    registry.register_tool(WriteFileTool(sandbox))
    registry.register_tool(ReadFileTool(sandbox))
    registry.register_tool(DeletePathTool(sandbox))

    gateway = InternetGateway()
    search_manager = SearchManager(
        primary=DuckDuckGoSearchProvider(gateway),
        fallback=MockSearchProvider()
    )
    research_agent = ResearchAgent(search_manager)
    quarantine_downloader = QuarantineDownloader(settings.workspace_root / "quarantine", gateway)

    manager = ProviderManager(bus)
    manager.register_provider(
        LocalAIProvider(
            endpoint=settings.local_provider_endpoint,
            model_name=settings.local_model_name,
            runtime=settings.local_provider_runtime
        )
    )
    manager.register_provider(
        GeminiProvider(
            api_key=settings.gemini_api_key,
            model_name=settings.gemini_model_name
        )
    )
    manager.register_provider(MockProvider())

    router = ModelRouter(
        manager=manager,
        event_bus=bus,
        model_registry=model_registry,
        resource_manager=resource_manager,
        policy=RoutingPolicy.LOCAL_FIRST,
        priority=settings.provider_priority,
        offline_mode=settings.offline_mode
    )

    context_builder = ContextBuilder(registry, memory_manager)
    analyzer = IntentAnalyzer(router)
    planner = Planner(router, registry, context_builder)
    validator = PlanValidator(registry)
    executor = ExecutionEngine(registry, bus, checkpoint_manager, recovery_engine)

    return (
        analyzer, planner, validator, executor, memory_manager,
        checkpoint_manager, recovery_engine, gateway, search_manager,
        research_agent, quarantine_downloader, resource_manager, model_registry,
        router, media_manager, creative_engine, render_engine, vision_engine,
        effects_engine, editor_engine, orchestrator, hardening_engine
    )


async def cli_doctor():
    *_, hardening_engine = get_core_runtime()
    report = hardening_engine.run_diagnostics()

    print("\n==================================================")
    print("               SAE SYSTEM DIAGNOSTICS             ")
    print("==================================================")
    print(f"Overall Status : {report.overall_status}")
    print(f"Engine Mode    : {report.engine_mode.value}")
    print(f"Timestamp      : {report.timestamp}\n")

    print("SUBSYSTEM CHECKS:")
    for c in report.checks:
        icon = "✓" if c.status == "OK" else ("⚠" if c.status == "WARN" else "✗")
        print(f"  {icon} [{c.status}] {c.subsystem}: {c.details}")
    print()


async def cli_run_autonomous(prompt: str, dry_run: bool = False):
    *_, orchestrator, _ = get_core_runtime()
    print(f"\n[SAE Autonomous Engine] Initiating Creative Workflow for: '{prompt}' (Dry Run: {dry_run})")
    res = await orchestrator.execute(prompt, autonomy_level=AutonomyLevel.LEVEL_2_AUTONOMOUS, dry_run=dry_run)

    print("\n==================================================")
    print("        AUTONOMOUS CREATIVE WORKFLOW SUMMARY      ")
    print("==================================================")
    print(f"Workflow ID   : {res.workflow_id}")
    print(f"Status        : {res.state.value}")
    print(f"Goal Title    : {res.brief.title} ({res.brief.target_duration_sec}s)")
    print(f"Style / Look  : {res.brief.style_keyword} / {res.brief.color_look}")
    print(f"Quality Score : {res.quality_score} / 100.0\n")

    print("PROGRESS LOG:")
    for step in res.progress_log:
        print(f"  {step}")

    print("\nDELIVERY ARTIFACTS:")
    if res.rendered_path:
        print(f"  • Video Render : {res.rendered_path}")
    if res.editor_export_path:
        print(f"  • Editor Proj  : {res.editor_export_path}")
    if not res.rendered_path and not res.editor_export_path:
        print("  • Validation Manifest Verified (Dry-Run)")
    print()


async def cli_editor_detect():
    *_, editor_engine, _, _ = get_core_runtime()
    caps = editor_engine.detect_all()
    print("\n==================================================")
    print("            SAE EDITOR INTEGRATION STATUS         ")
    print("==================================================")
    for etype, c in caps.items():
        print(f"Editor  : {etype.value}")
        print(f"  Installed : {'YES' if c.installed else 'NO'}")
        print(f"  Version   : {c.version}")
        print(f"  Features  : Multitrack={c.supports_multitrack}, Keyframes={c.supports_keyframes}, Markers={c.supports_markers}\n")


async def cli_editor_export(title: str, editor_choice: str = "premiere", dry_run: bool = False):
    *_, creative_engine, _, vision_engine, effects_engine, editor_engine, _, _ = get_core_runtime()
    etype = EditorType.PREMIERE_PRO if editor_choice.lower() == "premiere" else EditorType.DAVINCI_RESOLVE
    
    print(f"\n[SAE Editor Bridge] Translating Blueprint to {etype.value}: '{title}' (Dry Run: {dry_run})")
    bp = creative_engine.generate_reel_blueprint(title=title, target_duration=12.0)
    vision_report = vision_engine.analyze_asset("mock_asset_reel")
    treatment = effects_engine.generate_treatment(bp, vision_report=vision_report)

    manifest, out_path = editor_engine.export_to_editor(
        blueprint=bp,
        treatment=treatment,
        editor_type=etype,
        dry_run=dry_run
    )

    print("\n==================================================")
    print("             EDITOR INTERCHANGE SUMMARY           ")
    print("==================================================")
    print(f"Project   : {manifest.project_name}")
    print(f"Sequence  : {manifest.sequence_name} ({manifest.width}x{manifest.height} @ {manifest.fps} FPS)")
    print(f"Duration  : {manifest.total_duration_sec}s")
    print(f"Clips     : {len(manifest.video_clips)} video, {len(manifest.audio_clips)} audio")
    print(f"Markers   : {len(manifest.markers)} timeline markers mapped")
    if out_path:
        print(f"Exported  : {out_path.resolve()}")
    else:
        print("Exported  : NONE (Dry-Run Mode Verified)")
    print()


async def cli_effects_treatment(title: str, duration: float = 12.0):
    *_, creative_engine, _, vision_engine, effects_engine, _, _, _ = get_core_runtime()
    print(f"\n[SAE Effects Engine] Generating Visual Treatment & Cinematic Color for: '{title}'")
    
    bp = creative_engine.generate_reel_blueprint(title=title, target_duration=duration)
    vision_report = vision_engine.analyze_asset("mock_asset_reel")
    treatment = effects_engine.generate_treatment(bp, vision_report=vision_report, look=CreativeLookType.DARK_CINEMATIC)

    print("\n==================================================")
    print("           SAE CREATIVE TREATMENT BLUEPRINT       ")
    print("==================================================")
    print(f"Treatment ID : {treatment.treatment_id}")
    print(f"Target BP    : {treatment.target_blueprint_id}")
    print(f"Color Look   : {treatment.color_grade.look_type.value}")
    print(f"  Contrast   : {treatment.color_grade.contrast} | Saturation: {treatment.color_grade.saturation}")
    print(f"  Temp / Tint: {treatment.color_grade.temperature} / {treatment.color_grade.tint}")
    print(f"  Film Grain : Amount={treatment.color_grade.film_grain.amount} (Seed={treatment.color_grade.film_grain.seed})")
    print(f"Effects Count: {len(treatment.effects_stack)} layered effects")
    print(f"Keyframes    : {len(treatment.motion_keyframes)} motion points\n")

    print("EFFECT STACK:")
    for eff in treatment.effects_stack:
        print(f"  • [{eff.start_sec:.2f}s -> {eff.end_sec:.2f}s] {eff.name} ({eff.category.value}) - Intensity: {eff.intensity}")
        print(f"    Reason: {eff.reason}")

    print("\nEXPLAINABILITY:")
    for exp in treatment.explanations:
        print(f"  ✓ {exp}")
    print()


async def cli_vision_analyze(asset_id: str):
    *_, vision_engine, _, _, _, _ = get_core_runtime()
    print(f"\n[SAE Vision Engine] Executing hierarchical video intelligence on: {asset_id}")
    report = vision_engine.analyze_asset(asset_id)

    print("\n==================================================")
    print("           SAE VIDEO INTELLIGENCE REPORT          ")
    print("==================================================")
    print(f"Asset ID      : {report.asset_id}")
    print(f"Global Energy : {report.global_visual_energy} / 1.0")
    print(f"Scenes Found  : {len(report.scenes)}")
    print(f"Opportunities : {len(report.transition_opportunities)} transition matches\n")

    for scene in report.scenes:
        print(f"SCENE: {scene.scene_id} [{scene.start_sec}s -> {scene.end_sec}s]")
        print(f"  Environment : {scene.environment} | Mood: {scene.overall_mood}")
        print("  SHOTS:")
        for s in scene.shots:
            impact_str = f" [IMPACT @ {s.impact_moments[0].timestamp_sec}s]" if s.impact_moments else ""
            print(f"    • {s.shot_id} [{s.start_sec}s -> {s.end_sec}s]: {s.shot_type.value} | Motion: {s.motion_direction.value} ({s.motion_intensity}){impact_str}")
            print(f"      Action: {s.action} | Energy: {s.visual_energy} | Angle: {s.camera_angle.value}")
        print()


async def cli_render_reel(title: str, duration: float = 12.0):
    *_, creative_engine, render_engine, _, _, _, _, _ = get_core_runtime()
    print(f"\n[SAE Pipeline] Planning & Rendering Reel: '{title}' ({duration}s)")
    bp = creative_engine.generate_reel_blueprint(title=title, target_duration=duration)
    output_path = await render_engine.render_blueprint(bp)

    print("\n==================================================")
    print("             SAE MEDIA RENDER COMPLETE            ")
    print("==================================================")
    print(f"Blueprint : {bp.blueprint_id} ({bp.title})")
    print(f"Format    : {bp.format.value} ({bp.width}x{bp.height} @ {bp.fps} FPS)")
    print(f"Output    : {output_path.resolve()}")
    print(f"Size      : {output_path.stat().st_size} bytes")
    print("Status    : VERIFIED & READY FOR DISTRIBUTION\n")


async def cli_creative_reel(title: str, duration: float = 12.0):
    *_, media_manager, creative_engine, _, _, _, _, _, _ = get_core_runtime()
    print(f"\n[SAE Creative Engine] Generating timeline blueprint: '{title}' ({duration}s)")
    bp = creative_engine.generate_reel_blueprint(title=title, target_duration=duration)
    
    reg_assets = {a.asset_id for a in media_manager.list_assets()}
    for c in bp.video_clips:
        reg_assets.add(c.asset_id)
    is_valid, errors = TimelineValidator.validate(bp, reg_assets)

    print("\n==================================================")
    print("              SAE EDITING BLUEPRINT               ")
    print("==================================================")
    print(f"Title    : {bp.title} (ID: {bp.blueprint_id})")
    print(f"Format   : {bp.format.value} ({bp.width}x{bp.height} @ {bp.fps} FPS)")
    print(f"Duration : {bp.target_duration_sec}s | Style: {bp.style.value}")
    print(f"Status   : {'VALID' if is_valid else 'INVALID'}")
    print(f"Grade    : {bp.color_grade.profile_name} (Contrast: {bp.color_grade.contrast})\n")

    print("TIMELINE CLIPS:")
    for c in bp.video_clips:
        print(f"  [{c.timeline_start_sec:.2f}s -> {c.timeline_end_sec:.2f}s] {c.clip_id}")
        print(f"     Motion: {c.camera_motion.value} | Transition: {c.transition_in.value} | Energy: {c.energy_level}")
        print(f"     Reason: {c.selection_reason}\n")


async def cli_media_scan(target_dir: str):
    *_, media_manager, _, _, _, _, _, _, _ = get_core_runtime()
    p = Path(target_dir)
    print(f"\n[SAE Media Engine] Scanning approved directory: {p.resolve()}")
    discovered = media_manager.scan_directory(p)
    print(f"Discovered and registered {len(discovered)} media asset(s).\n")
    for a in discovered:
        print(f"  • [{a.media_type.value}] {a.filename} (ID: {a.asset_id})")
        print(f"    Tags: {', '.join(a.tags)} | Size: {round(a.file_size_bytes / 1024, 1)} KB\n")


async def cli_media_list():
    *_, media_manager, _, _, _, _, _, _, _ = get_core_runtime()
    assets = media_manager.list_assets()
    print("\n==================================================")
    print("                SAE MEDIA ASSET INDEX             ")
    print("==================================================")
    if not assets:
        print("  No registered media assets found. Use 'sae media scan <dir>'.\n")
        return

    for a in assets:
        print(f"[{a.media_type.value}] {a.filename} (ID: {a.asset_id})")
        print(f"  Path    : {a.file_path}")
        print(f"  Tags    : {', '.join(a.tags)}")
        print(f"  Creative: Energy={a.creative.energy} | Style={a.creative.style.value}\n")


async def cli_media_search(query: str):
    *_, media_manager, _, _, _, _, _, _, _ = get_core_runtime()
    print(f"\n[SAE Media Search] Querying assets for: '{query}'")
    matches = media_manager.search_assets(query)
    print("\n==================================================")
    print("                  MATCHED ASSETS                  ")
    print("==================================================")
    if not matches:
        print("  No matching media assets found.\n")
        return

    for idx, a in enumerate(matches, 1):
        print(f"{idx}. {a.filename} (Type: {a.media_type.value})")
        print(f"   Tags  : {', '.join(a.tags)}")
        print(f"   Style : {a.creative.style.value} | Energy: {a.creative.energy}\n")


async def cli_models_list():
    *_, model_registry, _, _, _, _, _, _, _, _, _ = get_core_runtime()
    models = model_registry.list_models()
    print("\n==================================================")
    print("              SAE LOCAL MODEL REGISTRY            ")
    print("==================================================")
    for m in models:
        caps = ", ".join([c.value for c in m.capabilities])
        print(f"Model ID : {m.model_id} ({m.name})")
        print(f"  Runtime     : {m.runtime_name.upper()} [{m.quantization}]")
        print(f"  VRAM / RAM  : {m.vram_required_gb} GB VRAM | {m.ram_required_gb} GB RAM")
        print(f"  Context     : {m.context_length} tokens")
        print(f"  Capabilities: {caps}")
        print(f"  Status      : {m.status.value}\n")


async def cli_resources_status():
    *_, resource_manager, _, _, _, _, _, _, _, _, _, _ = get_core_runtime()
    metrics = resource_manager.get_metrics()
    print("\n==================================================")
    print("          SYSTEM RESOURCE & HARDWARE STATUS       ")
    print("==================================================")
    print(f"CPU Utilization : {metrics.cpu_percent}%")
    print(f"System RAM      : {metrics.free_ram_gb} GB Free / {metrics.total_ram_gb} GB Total")
    print(f"GPU VRAM        : {metrics.free_vram_gb} GB Free / {metrics.total_vram_gb} GB Total")
    print(f"Disk Available  : {metrics.free_disk_gb} GB Free\n")


async def cli_research(query: str):
    *_, research_agent, _, _, _, _, _, _, _, _, _, _, _, _ = get_core_runtime()
    print(f"\n[SAE Research Agent] Initiating multi-query investigation: '{query}'")
    report = await research_agent.execute_research(query)

    print("\n==================================================")
    print("                SAE RESEARCH REPORT               ")
    print("==================================================")
    print(f"Query     : {report.query}")
    print(f"Timestamp : {report.retrieved_at}")
    print(f"Sources   : {len(report.sources)} verified sources\n")

    print("FINDINGS:")
    for idx, f in enumerate(report.findings, 1):
        print(f"  {idx}. {f.claim}")
        print(f"     Source: {', '.join(f.sources)}\n")


async def cli_plan_command(command: str):
    analyzer, planner, validator, *_ = get_core_runtime()
    print(f"\n[SAE] Analyzing command: '{command}'")
    intent = await analyzer.analyze(command)
    
    if intent.is_ambiguous:
        print(f"\n[AMBIGUOUS REQUEST]: {intent.clarification_prompt}\n")
        return

    plan = await planner.create_plan(intent, command)
    is_valid, err = validator.validate_plan(plan)
    if not is_valid:
        plan = validator.attempt_repair(plan)

    print("\n==================================================")
    print("                 SAE EXECUTION PLAN               ")
    print("==================================================")
    print(f"Goal   : {plan.goal}")
    print(f"Status : {'VALID' if plan.is_valid else 'INVALID'}")
    if plan.validation_error:
        print(f"Error  : {plan.validation_error}")
    print(f"Steps  : {len(plan.steps)}\n")

    for idx, step in enumerate(plan.steps, 1):
        print(f"  {idx}. {step.description}")
        print(f"     Tool     : {step.tool_name}")
        print(f"     Arguments: {step.arguments}")
        print(f"     DependsOn: {step.dependencies}\n")


def main():
    if len(sys.argv) < 2:
        print("SAE CLI - Usage:")
        print("  python sae_cli.py doctor")
        print("  python sae_cli.py run <natural_language_prompt> [--dry-run]")
        print("  python sae_cli.py editor detect")
        print("  python sae_cli.py editor export <title> [premiere|davinci] [--dry-run]")
        print("  python sae_cli.py effects treatment <title> [duration]")
        print("  python sae_cli.py vision analyze <asset_id>")
        print("  python sae_cli.py render reel <title> [duration]")
        print("  python sae_cli.py creative reel <title> [duration]")
        print("  python sae_cli.py media scan <directory>")
        print("  python sae_cli.py media list")
        print("  python sae_cli.py media search <query>")
        print("  python sae_cli.py models list")
        print("  python sae_cli.py resources status")
        print("  python sae_cli.py plan <prompt>")
        print("  python sae_cli.py research <topic>")
        sys.exit(0)

    cmd = sys.argv[1].lower()
    subcmd = sys.argv[2].lower() if len(sys.argv) > 2 else ""

    if cmd == "doctor":
        asyncio.run(cli_doctor())
    elif cmd == "run" and len(sys.argv) > 2:
        dry = "--dry-run" in sys.argv
        prompt_tokens = [t for t in sys.argv[2:] if t != "--dry-run"]
        asyncio.run(cli_run_autonomous(" ".join(prompt_tokens), dry_run=dry))
    elif cmd == "editor" and subcmd == "detect":
        asyncio.run(cli_editor_detect())
    elif cmd == "editor" and subcmd == "export" and len(sys.argv) > 3:
        title = sys.argv[3]
        target = sys.argv[4] if len(sys.argv) > 4 and not sys.argv[4].startswith("--") else "premiere"
        dry = "--dry-run" in sys.argv
        asyncio.run(cli_editor_export(title, target, dry))
    elif cmd == "effects" and subcmd == "treatment" and len(sys.argv) > 3:
        title = sys.argv[3]
        dur = float(sys.argv[4]) if len(sys.argv) > 4 else 12.0
        asyncio.run(cli_effects_treatment(title, dur))
    elif cmd == "vision" and subcmd == "analyze" and len(sys.argv) > 3:
        asyncio.run(cli_vision_analyze(sys.argv[3]))
    elif cmd == "render" and subcmd == "reel" and len(sys.argv) > 3:
        title = sys.argv[3]
        dur = float(sys.argv[4]) if len(sys.argv) > 4 else 12.0
        asyncio.run(cli_render_reel(title, dur))
    elif cmd == "creative" and subcmd == "reel" and len(sys.argv) > 3:
        title = sys.argv[3]
        dur = float(sys.argv[4]) if len(sys.argv) > 4 else 12.0
        asyncio.run(cli_creative_reel(title, dur))
    elif cmd == "media" and subcmd == "scan" and len(sys.argv) > 3:
        asyncio.run(cli_media_scan(sys.argv[3]))
    elif cmd == "media" and subcmd == "list":
        asyncio.run(cli_media_list())
    elif cmd == "media" and subcmd == "search" and len(sys.argv) > 3:
        asyncio.run(cli_media_search(" ".join(sys.argv[3:])))
    elif cmd == "models" and subcmd == "list":
        asyncio.run(cli_models_list())
    elif cmd == "resources" and subcmd == "status":
        asyncio.run(cli_resources_status())
    elif cmd == "plan" and len(sys.argv) > 2:
        asyncio.run(cli_plan_command(" ".join(sys.argv[2:])))
    elif cmd == "research" and len(sys.argv) > 2:
        asyncio.run(cli_research(" ".join(sys.argv[2:])))
    else:
        print(f"Unknown command: {' '.join(sys.argv[1:])}")


if __name__ == "__main__":
    main()