"""
N2NHU World Creator - One Shot World Generator
===============================================
Single command generates a complete, enriched, playable world:

  Step 1: Generate world structure (rooms, objects, sprites, physics)
  Step 2: Enrich room descriptions via Llama 3 / LLM
  Step 3: Pre-generate room images via Stable Diffusion
  Step 4: Enrich objects, sprites, transformations via Llama 3 / LLM

Usage:
  python create_world.py "Bewitched"
  python create_world.py "Area 51" --rooms 15
  python create_world.py "Barbie World" --rooms 10 --no-images
  python create_world.py "MASH 4077" --rooms 12 --output ./mash_world
  python create_world.py "Zork" --rooms 20 --physics magic,lock_key

N2NHU Labs for Applied Artificial Intelligence
"""

import argparse
import os
import sys
import time
import configparser


def banner(world_name: str):
    print()
    print('=' * 60)
    print('  N2NHU UNIVERSAL GAME ENGINE')
    print('  INFINITE IMPROBABILITY DRIVE')
    print('  N2NHU Labs for Applied Artificial Intelligence')
    print('=' * 60)
    print(f'  World:   {world_name}')
    print('=' * 60)
    print()


def step_header(num: int, title: str):
    print(f'\n{"─"*60}')
    print(f'  STEP {num}: {title}')
    print(f'{"─"*60}')


def load_drive_config(ini_path: str) -> dict:
    config = configparser.RawConfigParser()
    if os.path.exists(ini_path):
        config.read(ini_path, encoding='utf-8')
    cfg = {}
    if config.has_section('gpt4all'):
        cfg['gpt4all_host']    = config.get('gpt4all', 'host',    fallback='localhost')
        cfg['gpt4all_port']    = config.get('gpt4all', 'port',    fallback='4891')
        cfg['gpt4all_model']   = config.get('gpt4all', 'model',   fallback='Llama 3 8B Instruct')
        cfg['gpt4all_timeout'] = config.get('gpt4all', 'timeout', fallback='60')
    else:
        cfg['gpt4all_host']    = 'localhost'
        cfg['gpt4all_port']    = '4891'
        cfg['gpt4all_model']   = 'Llama 3 8B Instruct'
        cfg['gpt4all_timeout'] = '60'
    if config.has_section('claude_api'):
        cfg['claude_api_key'] = config.get('claude_api', 'api_key', fallback='')
        cfg['claude_model']   = config.get('claude_api', 'model',   fallback='claude-haiku-4-5-20251001')
    if config.has_section('huggingface'):
        cfg['huggingface_api_key'] = config.get('huggingface', 'api_key',     fallback='')
        cfg['huggingface_model']   = config.get('huggingface', 'llm_model',   fallback='meta-llama/Meta-Llama-3-8B-Instruct')
    if config.has_section('stable_diffusion'):
        cfg['sd_host'] = config.get('stable_diffusion', 'host', fallback='127.0.0.1')
        cfg['sd_port'] = config.get('stable_diffusion', 'port', fallback='7860')
    else:
        cfg['sd_host'] = '127.0.0.1'
        cfg['sd_port'] = '7860'
    return cfg


def console_progress(phase: str, current: int, total: int,
                     room_name: str, preview: str):
    bar_len = 25
    filled  = int(bar_len * current / max(1, total))
    bar     = '█' * filled + '░' * (bar_len - filled)
    pct     = int(100 * current / max(1, total))
    print(f'\r  [{bar}] {pct:3d}%  {room_name[:30]:<30}', end='', flush=True)
    if current == total:
        print()


def main():
    parser = argparse.ArgumentParser(
        prog='create_world',
        description='N2NHU One-Shot World Creator — Full Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  python create_world.py "Bewitched"
  python create_world.py "Area 51" --rooms 15
  python create_world.py "Barbie World" --rooms 10 --no-images
  python create_world.py "MASH 4077" --rooms 12 --output ./mash
  python create_world.py "Zork" --rooms 20 --physics magic,lock_key,crafting
  python create_world.py "Hogans Heroes" --rooms 10 --objects 12 --sprites 8

PHYSICS CHOICES:
  temperature, energy, lock_key, crafting, teleportation,
  disguise, explosives, bribery, magic, medical, growth, alien_tech
        """
    )
    parser.add_argument('world_name',
                        help='Name of the world to create (e.g. "Bewitched")')
    parser.add_argument('--rooms',    type=int, default=8,
                        help='Number of rooms (default 8)')
    parser.add_argument('--objects',  type=int, default=10,
                        help='Number of objects to generate (default 10)')
    parser.add_argument('--sprites',  type=int, default=6,
                        help='Number of characters to generate (default 6)')
    parser.add_argument('--transforms', type=int, default=5,
                        help='Number of transformations (default 5)')
    parser.add_argument('--physics',  default='',
                        help='Comma-separated physics types (default: theme auto-select)')
    parser.add_argument('--output',   default='',
                        help='Output directory (default: ./<world_name>_world)')
    parser.add_argument('--no-images', action='store_true',
                        help='Skip SD image pre-generation')
    parser.add_argument('--no-enrich', action='store_true',
                        help='Skip LLM enrichment (structure only)')
    parser.add_argument('--config',   default='./improbability_drive.ini',
                        help='Path to improbability_drive.ini')
    parser.add_argument('--sd-host',  default='127.0.0.1')
    parser.add_argument('--sd-port',  type=int, default=7860)

    args = parser.parse_args()

    world_name = args.world_name.strip()
    output_dir = args.output or (
        './' + world_name.lower().replace(' ', '_').replace("'", '') + '_world'
    )
    os.makedirs(output_dir, exist_ok=True)

    banner(world_name)
    total_start = time.time()

    drive_config_early = load_drive_config(args.config)
    drive_config_early['sd_host'] = args.sd_host
    drive_config_early['sd_port'] = str(args.sd_port)

    from llm_providers import build_provider_chain
    from llm_theme_classifier import LLMThemeClassifier
    from theme_engine import ThemeEngine
    from world_model import PhysicsType, WorldTheme
    from world_interview import WorldKnowledgeInterview

    _engine    = ThemeEngine()
    _chain_pre = build_provider_chain(drive_config_early)

    # ── STEP 0: WORLD KNOWLEDGE INTERVIEW ────────────────────
    # Jim's architecture: establish ONE validated WorldContext before
    # any generation. All downstream steps consume this instead of doing
    # isolated LLM discovery that can go wrong independently.
    #
    # Multi-turn dialogue:
    #   T1: "Describe ADAM 12" -> "1968 LAPD patrol car TV show..."
    #   T2: Extract structured facts -> genre, setting, chars, objects
    #   T3: "Are these facts correct?" -> Yes / No
    #   T4: If No, correct and re-confirm
    print(f'\n  Interviewing LLM about: {world_name!r}')
    _interview = WorldKnowledgeInterview(_chain_pre)
    _ctx = _interview.run(world_name)

    if _ctx.is_valid():
        print(f'  ✅ World context: {_ctx.anchor_summary()[:80]}')
        print(f'     Confidence: {_ctx.confidence}  Method: {_ctx.method}')
    else:
        print(f'  ⚠️  World context incomplete — downstream steps will self-discover')

    # ── STEP 0a: Theme Classification ────────────────────────
    _classifier = LLMThemeClassifier(
        provider_chain     = _chain_pre,
        keyword_classifier = _engine.classify,
    )

    print(f'\n  Classifying theme for: {world_name!r}')
    llm_theme = _classifier.classify(world_name)
    print(f'  ✅ Theme: {llm_theme.value}  (method: {_classifier.last_method})')

    # ── STEP 0b: LLM Room Name Discovery ─────────────────────
    # Two-step room naming (Jim's design):
    #   Q1: "What is the usual setting of THREE'S COMPANY?"
    #       Llama: "APARTMENT"
    #   Q2: "What are 10 room names in a THREE'S COMPANY APARTMENT?"
    #       Llama: "Living Room, Kitchen, Jack's Bedroom, ..."
    #
    # Falls back to theme engine suggested_room_prefixes if LLM fails.

    from llm_room_namer import LLMRoomNamer

    _theme_defaults_pre = _engine.get_defaults_for_theme(llm_theme)
    _room_namer = LLMRoomNamer(provider_chain=_chain_pre)

    print(f'\n  Generating room names for: {world_name!r}')
    llm_room_names = _room_namer.generate_names(
        world_name     = world_name,
        count          = args.rooms,
        fallback_names = _theme_defaults_pre.suggested_room_prefixes,
        world_context  = _ctx,
    )
    print(f'  ✅ Rooms: {", ".join(llm_room_names[:5])}{"..." if len(llm_room_names) > 5 else ""}')
    print(f'  ✅ Setting: {_room_namer.last_setting}  (method: {_room_namer.last_method})')

    # ── STEP 1: Generate World Structure ─────────────────────
    step_header(1, 'GENERATE WORLD STRUCTURE')

    from generator import WorldGenerator, GeneratorRequest
    from theme_engine import get_setting_suffix

    physics_map   = {p.value: p for p in PhysicsType}
    physics_types = []
    if args.physics:
        for p in args.physics.split(','):
            p = p.strip()
            if p in physics_map:
                physics_types.append(physics_map[p])
            else:
                print(f'  WARNING: Unknown physics "{p}" — skipping')

    # ── Setting-aware SD suffix ───────────────────────────────
    # Jim's refinement: "if GILLIGANS ISLAND is a SITCOM, what is
    # the SETTING where the ACTION takes place?"
    # The room namer already discovered the physical setting.
    # Use it to override the genre's default SD scene suffix so
    # a tropical island doesn't render as a cozy American living room.
    _theme_defaults_sd  = _engine.get_defaults_for_theme(llm_theme)
    _discovered_setting = _room_namer.last_setting or ''
    _sd_suffix, _sd_negative = get_setting_suffix(
        _discovered_setting,
        _theme_defaults_sd.sd_scene_suffix,
        _theme_defaults_sd.sd_negative_prompt,
    )
    if _discovered_setting and _sd_suffix != _theme_defaults_sd.sd_scene_suffix:
        print(f'  ✅ SD suffix: overridden by setting {_discovered_setting!r}')
    else:
        print(f'  ✅ SD suffix: theme default ({llm_theme.value})')

    request = GeneratorRequest(
        world_name        = world_name,
        room_count        = args.rooms,
        physics_types     = physics_types,
        output_dir        = output_dir,
        sd_host           = args.sd_host,
        sd_port           = args.sd_port,
        custom_theme      = llm_theme,        # LLM-classified theme
        custom_room_names = llm_room_names,   # LLM-discovered room names
        sd_scene_suffix   = _sd_suffix,       # setting-aware SD suffix
    )

    gen    = WorldGenerator()
    result = gen.generate(request)

    if not result.success:
        print(f'\n  ❌ Structure generation failed:')
        for err in result.validation_errors[:5]:
            print(f'     {err}')
        sys.exit(1)

    print(f'  ✅ Theme:    {result.theme_used.value if result.theme_used else "auto"}')
    print(f'  ✅ Rooms:    {args.rooms}')
    print(f'  ✅ Physics:  {[p.value for p in physics_types] or "theme defaults"}')
    print(f'  ✅ Files:    {len(result.written_files)} INI files written')
    print(f'  ✅ Output:   {output_dir}')

    if args.no_enrich:
        elapsed = time.time() - total_start
        print(f'\n{"="*60}')
        print(f'  World structure complete in {elapsed:.1f}s')
        print(f'  (--no-enrich flag set — skipping LLM enrichment)')
        print(f'  Output: {output_dir}')
        sys.exit(0)

    # Load drive config
    drive_config = load_drive_config(args.config)
    drive_config['sd_host'] = args.sd_host
    drive_config['sd_port'] = str(args.sd_port)

    # ── STEP 2: Enrich Room Descriptions ─────────────────────
    step_header(2, 'ENRICH ROOM DESCRIPTIONS (Llama 3)')

    from llm_providers import build_provider_chain
    from batch_generator import RoomDescriptionEnricher

    chain    = build_provider_chain(drive_config)
    enricher = RoomDescriptionEnricher(chain)

    print(f'  Active provider: {chain.detect_and_report().split("Active provider:")[1].strip() if "Active provider:" in chain.detect_and_report() else "detecting..."}')

    rooms_ini = os.path.join(output_dir, 'rooms.ini')
    desc_result = enricher.enrich(
        rooms_ini_path = rooms_ini,
        world_name     = world_name,
        progress_cb    = console_progress,
    )
    print(f'  ✅ {desc_result["enriched"]} room descriptions enriched')
    print(f'  ✅ Provider: {desc_result["provider"]}')

    # ── STEP 3: Pre-Generate Room Images ─────────────────────
    if not args.no_images:
        step_header(3, 'PRE-GENERATE ROOM IMAGES (Stable Diffusion)')

        from batch_generator import StaticImageGenerator

        img_gen = StaticImageGenerator(args.sd_host, args.sd_port)

        if img_gen.is_available():
            sd_ini = os.path.join(output_dir, 'stablediffusion.ini')
            img_result = img_gen.generate_all(
                rooms_ini_path = rooms_ini,
                sd_ini_path    = sd_ini,
                output_dir     = output_dir,
                progress_cb    = console_progress,
            )
            print(f'  ✅ {img_result["saved"]} images pre-generated')
            print(f'  ✅ Saved to: {img_result["dir"]}')
            print(f'  ✅ image_mode = static written to stablediffusion.ini')
        else:
            print(f'  ⚠️  SD not available at {args.sd_host}:{args.sd_port}')
            print(f'  ⚠️  Images will generate at runtime (realtime mode)')
    else:
        print(f'\n  (--no-images flag set — skipping image generation)')

    # ── STEP 4: Enrich Objects, Sprites, Transforms ──────────
    step_header(4, 'ENRICH OBJECTS / CHARACTERS / TRANSFORMATIONS (Llama 3)')

    from content_enricher import WorldContentEnricher

    content = WorldContentEnricher(chain)
    content_result = content.enrich_all(
        output_dir      = output_dir,
        world_name      = world_name,
        object_count    = args.objects,
        sprite_count    = args.sprites,
        transform_count = args.transforms,
        progress_cb     = console_progress,
        world_context   = _ctx,
    )

    print(f'  ✅ {content_result.get("objects", 0)} objects written')
    print(f'  ✅ {content_result.get("sprites", 0)} characters written')
    print(f'  ✅ {content_result.get("transforms", 0)} transformations written')

    # ── STEP 5: Post-Enrichment Matrix Validation ─────────────
    # The algebraic guarantee: NOTHING leaves the pipeline broken.
    # Content enricher rewrites objects/sprites with LLM data.
    # Those files are not covered by the Stage 11 round-trip check
    # (which ran before enrichment). This final pass re-reads ALL
    # six INI files and checks every cross-reference.
    # Any broken exit, object location, or sprite spawn is
    # auto-repaired rather than letting the player "be nowhere."
    step_header(5, 'MATRIX VALIDATION (zero-invalid guarantee)')

    from validation_engine import RoundTripVerifier
    import configparser as _cp

    final_verifier = RoundTripVerifier()
    final_result = final_verifier.verify(output_dir, world_name)

    if final_result.is_valid:
        print(f'  ✅ All cross-references valid — zero broken exits')
    else:
        print(f'  ⚠️  {len(final_result.errors)} cross-reference error(s) found — auto-repairing...')

        # Auto-repair: read rooms.ini and remove any exit pointing
        # to a room that doesn't exist.  Better a missing exit than
        # a player trapped in "nowhere."
        rooms_ini = os.path.join(output_dir, 'rooms.ini')
        rooms_cfg = _cp.RawConfigParser()
        rooms_cfg.read(rooms_ini, encoding='utf-8')
        valid_rooms = set(rooms_cfg.sections())

        DIRECTIONS = ['north','south','east','west','up','down',
                      'northeast','northwest','southeast','southwest','enter','exit']
        repaired = 0
        for section in rooms_cfg.sections():
            for d in DIRECTIONS:
                if rooms_cfg.has_option(section, d):
                    target = rooms_cfg.get(section, d)
                    if target not in valid_rooms:
                        rooms_cfg.remove_option(section, d)
                        print(f'    Removed broken exit: [{section}].{d} -> {target!r}')
                        repaired += 1

        if repaired:
            with open(rooms_ini, 'w', encoding='utf-8') as f:
                f.write(f'# Room Definitions - {world_name}\n')
                f.write(f'# Auto-repaired by Matrix Validator: {repaired} broken exits removed\n\n')
                rooms_cfg.write(f)

        # Also repair object locations
        objects_ini = os.path.join(output_dir, 'objects.ini')
        obj_cfg = _cp.RawConfigParser()
        obj_cfg.read(objects_ini, encoding='utf-8')
        valid_rooms_objs = set(rooms_cfg.sections())  # use repaired set

        obj_repaired = 0
        for section in obj_cfg.sections():
            if obj_cfg.has_option(section, 'location'):
                loc = obj_cfg.get(section, 'location')
                if loc and loc not in ('none', '') and loc not in valid_rooms_objs:
                    # Move to entrance or first room
                    fallback = 'entrance' if 'entrance' in valid_rooms_objs \
                               else list(valid_rooms_objs)[0]
                    obj_cfg.set(section, 'location', fallback)
                    print(f'    Relocated [{section}] from {loc!r} -> {fallback!r}')
                    obj_repaired += 1

        if obj_repaired:
            with open(objects_ini, 'w', encoding='utf-8') as f:
                f.write(f'# Object Definitions - {world_name}\n')
                f.write(f'# Auto-repaired by Matrix Validator: {obj_repaired} locations fixed\n\n')
                obj_cfg.write(f)

        # Also repair sprite spawn_rooms
        sprites_ini = os.path.join(output_dir, 'sprites.ini')
        spr_cfg = _cp.RawConfigParser()
        spr_cfg.read(sprites_ini, encoding='utf-8')

        spr_repaired = 0
        for section in spr_cfg.sections():
            if spr_cfg.has_option(section, 'spawn_rooms'):
                raw = spr_cfg.get(section, 'spawn_rooms')
                rooms_list = [r.strip() for r in raw.split(',') if r.strip()]
                valid_spawns = [r for r in rooms_list if r in valid_rooms_objs]
                if len(valid_spawns) < len(rooms_list):
                    fallback = 'entrance' if 'entrance' in valid_rooms_objs \
                               else list(valid_rooms_objs)[0]
                    fixed = valid_spawns if valid_spawns else [fallback]
                    spr_cfg.set(section, 'spawn_rooms', ', '.join(fixed))
                    print(f'    Fixed spawn_rooms [{section}]: {rooms_list} -> {fixed}')
                    spr_repaired += 1

        if spr_repaired:
            with open(sprites_ini, 'w', encoding='utf-8') as f:
                f.write(f'# Sprite Definitions - {world_name}\n')
                f.write(f'# Auto-repaired by Matrix Validator: {spr_repaired} spawn rooms fixed\n\n')
                spr_cfg.write(f)

        total_repaired = repaired + obj_repaired + spr_repaired
        print(f'  ✅ Auto-repair complete: {total_repaired} reference(s) fixed')

        # Final re-check
        final2 = final_verifier.verify(output_dir, world_name)
        if final2.is_valid:
            print(f'  ✅ Matrix is clean after repair')
        else:
            print(f'  ⚠️  {len(final2.errors)} residual issue(s) — see errors below:')
            for err in final2.errors[:10]:
                print(f'     {err}')

    # ── DONE ─────────────────────────────────────────────────
    elapsed = time.time() - total_start
    mins    = int(elapsed // 60)
    secs    = int(elapsed % 60)

    print(f'\n{"="*60}')
    print(f'  ✅ {world_name.upper()} IS READY!')
    print(f'{"="*60}')
    print(f'  Rooms:          {args.rooms}')
    print(f'  Objects:        {content_result.get("objects", 0)}')
    print(f'  Characters:     {content_result.get("sprites", 0)}')
    print(f'  Transformations:{content_result.get("transforms", 0)}')
    print(f'  Images:         {"pre-generated (static)" if not args.no_images else "realtime"}')
    print(f'  Total time:     {mins}m {secs}s')
    print(f'  Output:         {os.path.abspath(output_dir)}')
    print(f'{"="*60}')
    print(f'\n  Copy {output_dir}/ to your game engine config/ folder.')
    print(f'  Launch ZORK_RPG_Server.exe. Your world is ready.\n')


if __name__ == '__main__':
    main()
