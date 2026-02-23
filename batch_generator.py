"""
N2NHU Infinite Improbability Drive - Batch Generator
======================================================
Runs after the core generator has written the 6 INI files.

Phase 1 — Room Descriptions:
  For each room: call LLM provider chain → write back to rooms.ini

Phase 2 — Room Images (optional, if image_mode = static):
  For each room: call SD → save to images/ folder

This is the "shower insight" — generate everything at world creation time
so runtime needs zero AI infrastructure to play.

Progress bar shows room-by-room with live description preview.

N2NHU Labs for Applied Artificial Intelligence
"""

import configparser
import os
import time
import base64
import requests
from typing import Optional, Callable
from llm_providers import build_provider_chain, ProviderChain


# ── Progress callback type ───────────────────────────────────
# Called with (phase, current, total, room_name, preview_text)
ProgressCallback = Callable[[str, int, int, str, str], None]


def _console_progress(phase: str, current: int, total: int,
                      room_name: str, preview: str):
    """Default console progress — used when no GUI callback provided."""
    bar_len = 30
    filled  = int(bar_len * current / max(1, total))
    bar     = '█' * filled + '░' * (bar_len - filled)
    pct     = int(100 * current / max(1, total))
    print(f'\r[{bar}] {pct:3d}%%  {phase}: {room_name[:30]:<30}', end='', flush=True)
    if current == total:
        print()  # newline on completion


# ── Room Description Enricher ────────────────────────────────

class RoomDescriptionEnricher:
    """
    Reads rooms.ini, generates LLM descriptions for each room,
    writes enriched descriptions back to rooms.ini.
    """

    def __init__(self, provider_chain: ProviderChain):
        self.chain = provider_chain

    def enrich(self, rooms_ini_path: str, world_name: str,
               progress_cb: ProgressCallback = None) -> dict:
        """
        Enrich all rooms in rooms.ini with LLM-generated descriptions.
        Returns: {room_id: description} for all rooms processed.
        """
        if progress_cb is None:
            progress_cb = _console_progress

        # Read existing rooms.ini
        config = configparser.RawConfigParser()
        config.read(rooms_ini_path, encoding='utf-8')
        sections = config.sections()

        results = {}
        errors  = []

        for i, section in enumerate(sections, 1):
            room_name = config.get(section, 'name', fallback=section)
            progress_cb('📝 Descriptions', i, len(sections), room_name, '...')

            # Generate description
            desc = self.chain.generate(world_name, room_name)

            if desc:
                # Write back — escape % for configparser
                escaped = desc.replace('%', '%%')
                config.set(section, 'description', escaped)
                results[section] = desc
            else:
                errors.append(section)

        # Write enriched rooms.ini back
        with open(rooms_ini_path, 'w', encoding='utf-8') as f:
            f.write(f'# Room Definitions - {world_name}\n')
            f.write(f'# Descriptions enriched by Infinite Improbability Drive\n')
            f.write(f'# Provider: {self.chain.last_provider}\n\n')
            config.write(f)

        progress_cb('📝 Descriptions', len(sections), len(sections),
                    'Complete', f'{len(results)} rooms enriched')

        return {
            'enriched': len(results),
            'errors':   errors,
            'provider': self.chain.last_provider,
        }


# ── Static Image Pre-Generator ───────────────────────────────

class StaticImageGenerator:
    """
    Pre-generates images for all rooms via Stable Diffusion.
    Saves to images/ subfolder alongside INI files.
    
    With image_mode = static in stablediffusion.ini,
    the engine reads from images/ instead of calling SD at runtime.
    """

    def __init__(self, sd_host: str = '127.0.0.1', sd_port: int = 7860):
        self.sd_host = sd_host
        self.sd_port = sd_port
        self.base_url = f'http://{sd_host}:{sd_port}'

    def is_available(self) -> bool:
        try:
            r = requests.get(f'{self.base_url}/sdapi/v1/sd-models', timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def generate_room_image(self, room_id: str, room_name: str,
                            description: str, scene_suffix: str,
                            negative_prompt: str, output_dir: str) -> Optional[str]:
        """Generate and save one room image. Returns saved path or None."""
        prompt = f"{room_name}, {description[:100]}, {scene_suffix}"

        payload = {
            'prompt':          prompt,
            'negative_prompt': negative_prompt,
            'steps':           25,
            'width':           512,
            'height':          512,
            'cfg_scale':       7.5,
            'sampler_name':    'DPM++ 2M',
        }

        try:
            r = requests.post(
                f'{self.base_url}/sdapi/v1/txt2img',
                json=payload,
                timeout=120
            )
            r.raise_for_status()
            data = r.json()

            images_dir = os.path.join(output_dir, 'images')
            os.makedirs(images_dir, exist_ok=True)

            img_b64  = data['images'][0]
            img_data = base64.b64decode(img_b64)
            img_path = os.path.join(images_dir, f'{room_id}.jpg')

            with open(img_path, 'wb') as f:
                f.write(img_data)

            return img_path

        except Exception as e:
            return None

    def generate_all(self, rooms_ini_path: str, sd_ini_path: str,
                     output_dir: str, progress_cb: ProgressCallback = None) -> dict:
        """Pre-generate images for all rooms."""
        if progress_cb is None:
            progress_cb = _console_progress

        # Read rooms
        rooms_config = configparser.RawConfigParser()
        rooms_config.read(rooms_ini_path, encoding='utf-8')

        # Read SD config for prompts
        sd_config = configparser.RawConfigParser()
        sd_config.read(sd_ini_path, encoding='utf-8')

        scene_suffix    = ''
        negative_prompt = ''
        if sd_config.has_section('prompt_style'):
            scene_suffix    = sd_config.get('prompt_style', 'scene_suffix',    fallback='')
            negative_prompt = sd_config.get('prompt_style', 'negative_prompt', fallback='')

        sections = rooms_config.sections()
        saved    = []
        errors   = []

        for i, section in enumerate(sections, 1):
            room_name = rooms_config.get(section, 'name', fallback=section)
            desc      = rooms_config.get(section, 'description', fallback='')
            # Unescape %% for SD prompt use
            desc = desc.replace('%%', '%')

            progress_cb('🎨 Images', i, len(sections), room_name, 'Generating...')

            path = self.generate_room_image(
                room_id         = section,
                room_name       = room_name,
                description     = desc,
                scene_suffix    = scene_suffix,
                negative_prompt = negative_prompt,
                output_dir      = output_dir,
            )

            if path:
                saved.append(path)
            else:
                errors.append(section)

        progress_cb('🎨 Images', len(sections), len(sections),
                    'Complete', f'{len(saved)} images saved')

        # Update stablediffusion.ini to use static mode
        if saved:
            self._set_static_mode(sd_ini_path)

        return {
            'saved':  len(saved),
            'errors': errors,
            'dir':    os.path.join(output_dir, 'images'),
        }

    def _set_static_mode(self, sd_ini_path: str):
        """Set image_mode = static in stablediffusion.ini."""
        config = configparser.RawConfigParser()
        config.read(sd_ini_path, encoding='utf-8')
        if config.has_section('settings'):
            config.set('settings', 'image_mode', 'static')
            config.set('settings', 'images_dir', 'images')
            with open(sd_ini_path, 'w', encoding='utf-8') as f:
                config.write(f)


# ── Master Batch Orchestrator ─────────────────────────────────

class ImprobabilityDrive:
    """
    The complete Infinite Improbability Drive.
    Runs after the core generator has written 6 INI files.
    
    Phases:
      1. Detect available providers
      2. Enrich room descriptions via LLM
      3. Pre-generate room images via SD (if requested)
      4. Update INI files with enriched content
    """

    def __init__(self, output_dir: str, llm_config: dict = None,
                 generate_images: bool = True):
        self.output_dir      = output_dir
        self.generate_images = generate_images
        self.llm_config      = llm_config or {}

        self.rooms_ini   = os.path.join(output_dir, 'rooms.ini')
        self.sd_ini      = os.path.join(output_dir, 'stablediffusion.ini')

        # Build provider chain
        self.llm_chain   = build_provider_chain(self.llm_config)

        # SD image generator
        sd_host = self.llm_config.get('sd_host', '127.0.0.1')
        sd_port = int(self.llm_config.get('sd_port', 7860))
        self.image_gen   = StaticImageGenerator(sd_host, sd_port)

    def detect(self) -> str:
        """Detect and report available providers."""
        lines = [self.llm_chain.detect_and_report()]
        sd_ok = self.image_gen.is_available()
        lines.append(f'\n  {"✅" if sd_ok else "❌"}  Stable Diffusion '
                     f'({self.image_gen.sd_host}:{self.image_gen.sd_port})')
        return '\n'.join(lines)

    def estimate_time(self, room_count: int) -> str:
        """Estimate generation time based on available providers."""
        llm_status = self.llm_chain.detect()
        
        # GPT4All local: ~15-25s per room on CPU
        # Claude API: ~3-5s per room
        # HuggingFace: ~10-20s per room
        # Template: ~0s

        for name, avail in llm_status.items():
            if not avail:
                continue
            if 'GPT4All' in name:
                secs_per_room = 20
                break
            elif 'Claude' in name:
                secs_per_room = 4
                break
            elif 'HuggingFace' in name:
                secs_per_room = 15
                break
            else:
                secs_per_room = 0
                break
        else:
            secs_per_room = 0

        llm_secs = room_count * secs_per_room
        sd_secs  = room_count * 8 if self.generate_images else 0
        total    = llm_secs + sd_secs

        if total < 60:
            return f'~{total} seconds'
        elif total < 3600:
            return f'~{total // 60} minutes {total % 60} seconds'
        else:
            return f'~{total // 3600}h {(total % 3600) // 60}m'

    def run(self, world_name: str,
            progress_cb: ProgressCallback = None) -> dict:
        """
        Run the complete enrichment pipeline.
        Returns summary dict with counts and provider info.
        """
        if progress_cb is None:
            progress_cb = _console_progress

        results = {
            'world_name':  world_name,
            'descriptions': {},
            'images':       {},
            'errors':       [],
        }

        start_time = time.time()

        # ── Phase 1: Room Description Enrichment ─────────────
        print(f'\n📝 Phase 1: Enriching room descriptions...')
        print(f'   Provider chain: {self.llm_chain.detect_and_report()}')

        enricher = RoomDescriptionEnricher(self.llm_chain)
        desc_result = enricher.enrich(
            rooms_ini_path = self.rooms_ini,
            world_name     = world_name,
            progress_cb    = progress_cb,
        )
        results['descriptions'] = desc_result
        print(f'\n   ✅ {desc_result["enriched"]} descriptions generated '
              f'via {desc_result["provider"]}')

        # ── Phase 2: Static Image Pre-Generation ─────────────
        if self.generate_images:
            if self.image_gen.is_available():
                print(f'\n🎨 Phase 2: Pre-generating room images...')
                img_result = self.image_gen.generate_all(
                    rooms_ini_path = self.rooms_ini,
                    sd_ini_path    = self.sd_ini,
                    output_dir     = self.output_dir,
                    progress_cb    = progress_cb,
                )
                results['images'] = img_result
                print(f'\n   ✅ {img_result["saved"]} images saved to {img_result["dir"]}')
                print(f'   ✅ image_mode = static written to stablediffusion.ini')
            else:
                print(f'\n🎨 Phase 2: SD not available — skipping image pre-generation')
                print(f'   Images will be generated at runtime (realtime mode)')
                results['images'] = {'saved': 0, 'errors': [], 'dir': None}

        elapsed = time.time() - start_time
        results['elapsed'] = f'{elapsed:.1f}s'

        print(f'\n{"="*50}')
        print(f'✅ Infinite Improbability Drive complete!')
        print(f'   {desc_result["enriched"]} descriptions enriched')
        if self.generate_images:
            saved = results['images'].get('saved', 0)
            print(f'   {saved} images pre-generated')
        print(f'   Total time: {results["elapsed"]}')

        return results


# ── Quick test ───────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    output_dir = sys.argv[1] if len(sys.argv) > 1 else './generated_world'
    world_name = sys.argv[2] if len(sys.argv) > 2 else 'Bewitched'

    if not os.path.exists(os.path.join(output_dir, 'rooms.ini')):
        print(f'ERROR: No rooms.ini found in {output_dir}')
        print('Run the generator first to create a world.')
        sys.exit(1)

    drive = ImprobabilityDrive(
        output_dir      = output_dir,
        generate_images = True,
        llm_config      = {
            'gpt4all_host':  'localhost',
            'gpt4all_port':  '4891',
            'gpt4all_model': 'Llama 3 8B Instruct',
        }
    )

    print(drive.detect())
    print(f'\nEstimated time: {drive.estimate_time(10)}')
    print()

    drive.run(world_name=world_name)
