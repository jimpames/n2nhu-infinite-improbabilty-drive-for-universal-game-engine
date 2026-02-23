"""
N2NHU Infinite Improbability Drive - Enrichment Runner
=======================================================
Run AFTER the generator has created a world.
Enriches room descriptions via LLM and optionally
pre-generates all room images via Stable Diffusion.

Usage:
    python enrich.py --world "Bewitched" --dir ./generated_world
    python enrich.py --world "Barbie World" --dir ./barbie_world --no-images
    python enrich.py --world "Area 51" --dir ./area51 --detect

N2NHU Labs for Applied Artificial Intelligence
"""

import argparse
import configparser
import os
import sys
import time


def load_drive_config(ini_path: str) -> dict:
    """Load improbability_drive.ini into a flat config dict."""
    config = configparser.RawConfigParser()
    
    if os.path.exists(ini_path):
        config.read(ini_path, encoding='utf-8')
    
    cfg = {}
    
    # GPT4All
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

    # Claude
    if config.has_section('claude_api'):
        cfg['claude_api_key'] = config.get('claude_api', 'api_key', fallback='')
        cfg['claude_model']   = config.get('claude_api', 'model',
                                           fallback='claude-haiku-4-5-20251001')

    # HuggingFace
    if config.has_section('huggingface'):
        cfg['huggingface_api_key'] = config.get('huggingface', 'api_key', fallback='')
        cfg['huggingface_model']   = config.get('huggingface', 'llm_model',
                                                fallback='meta-llama/Meta-Llama-3-8B-Instruct')

    # SD
    if config.has_section('stable_diffusion'):
        cfg['sd_host'] = config.get('stable_diffusion', 'host', fallback='127.0.0.1')
        cfg['sd_port'] = config.get('stable_diffusion', 'port', fallback='7860')
    else:
        cfg['sd_host'] = '127.0.0.1'
        cfg['sd_port'] = '7860'

    return cfg


def console_progress_bar(phase: str, current: int, total: int,
                          room_name: str, preview: str):
    """Rich console progress bar with room name and preview."""
    bar_len = 25
    filled  = int(bar_len * current / max(1, total))
    bar     = '█' * filled + '░' * (bar_len - filled)
    pct     = int(100 * current / max(1, total))
    
    # Truncate room name for display
    name_display = room_name[:28].ljust(28)
    
    print(f'\r  [{bar}] {pct:3d}%%  {name_display}', end='', flush=True)
    
    if current == total:
        print(f'\n  {phase} complete — {total} rooms processed')


def run_enrichment(world_name: str, output_dir: str,
                   generate_images: bool, config_path: str,
                   detect_only: bool = False):

    from batch_generator import ImprobabilityDrive

    rooms_ini = os.path.join(output_dir, 'rooms.ini')
    if not os.path.exists(rooms_ini):
        print(f'\nERROR: No rooms.ini found in: {output_dir}')
        print('Run the generator first to create a world.')
        print('  python __main__.py --name "Bewitched" --output ./my_world')
        sys.exit(1)

    # Count rooms
    cfg = configparser.RawConfigParser()
    cfg.read(rooms_ini, encoding='utf-8')
    room_count = len(cfg.sections())

    # Load drive config
    drive_config = load_drive_config(config_path)

    # Build drive
    drive = ImprobabilityDrive(
        output_dir      = output_dir,
        generate_images = generate_images,
        llm_config      = drive_config,
    )

    print(f'\n{"="*55}')
    print(f'  N2NHU INFINITE IMPROBABILITY DRIVE')
    print(f'  N2NHU Labs for Applied Artificial Intelligence')
    print(f'{"="*55}')
    print(f'  World:      {world_name}')
    print(f'  Rooms:      {room_count}')
    print(f'  Output:     {output_dir}')
    print(f'  Images:     {"pre-generate (static)" if generate_images else "skip"}')

    # Provider detection
    print(f'\n{drive.detect()}')

    if detect_only:
        return

    # Time estimate
    est = drive.estimate_time(room_count)
    print(f'\n  Estimated time: {est}')
    print(f'\n  Starting enrichment...')
    print(f'{"="*55}\n')

    # Run with progress
    start = time.time()

    def progress(phase, current, total, room_name, preview):
        console_progress_bar(phase, current, total, room_name, preview)

    results = drive.run(world_name=world_name, progress_cb=progress)

    elapsed = time.time() - start
    mins    = int(elapsed // 60)
    secs    = int(elapsed % 60)

    print(f'\n{"="*55}')
    print(f'  ENRICHMENT COMPLETE')
    print(f'{"="*55}')
    print(f'  Descriptions: {results["descriptions"].get("enriched", 0)} rooms enriched')
    print(f'  Provider:     {results["descriptions"].get("provider", "unknown")}')

    if generate_images:
        img_count = results['images'].get('saved', 0)
        img_dir   = results['images'].get('dir', '')
        print(f'  Images:       {img_count} pre-generated')
        if img_dir:
            print(f'  Images dir:   {img_dir}')

    print(f'  Total time:   {mins}m {secs}s')
    print(f'\n  Your world is ready. Drop the folder into the')
    print(f'  game engine config/ directory and play.\n')


def main():
    parser = argparse.ArgumentParser(
        prog='enrich',
        description='N2NHU Infinite Improbability Drive — World Enrichment',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  python enrich.py --world "Bewitched" --dir ./generated_world
  python enrich.py --world "Barbie World" --dir ./barbie --no-images
  python enrich.py --world "Area 51" --dir ./area51 --detect
  python enrich.py --world "MASH 4077" --dir ./mash --config ./my_drive.ini

WORKFLOW:
  1. Generate world:   python __main__.py --name "Bewitched" --output ./my_world
  2. Enrich world:     python enrich.py --world "Bewitched" --dir ./my_world
  3. Play:             Copy my_world/ to game engine config/
        """
    )
    parser.add_argument('--world',    required=True,
                        help='World name (must match what was generated)')
    parser.add_argument('--dir',      default='./generated_world',
                        help='Output directory containing rooms.ini etc.')
    parser.add_argument('--no-images', action='store_true',
                        help='Skip image pre-generation (descriptions only)')
    parser.add_argument('--detect',   action='store_true',
                        help='Detect available providers only, do not enrich')
    parser.add_argument('--config',   default='./improbability_drive.ini',
                        help='Path to improbability_drive.ini config file')
    parser.add_argument('--model',    default='',
                        help='Override GPT4All model name')

    args = parser.parse_args()

    # Model override
    if args.model:
        # Write model override into a temp config section
        cfg = configparser.RawConfigParser()
        if os.path.exists(args.config):
            cfg.read(args.config)
        if not cfg.has_section('gpt4all'):
            cfg.add_section('gpt4all')
        cfg.set('gpt4all', 'model', args.model)
        with open(args.config, 'w') as f:
            cfg.write(f)
        print(f'Model set to: {args.model}')

    run_enrichment(
        world_name      = args.world,
        output_dir      = args.dir,
        generate_images = not args.no_images,
        config_path     = args.config,
        detect_only     = args.detect,
    )


if __name__ == '__main__':
    main()
