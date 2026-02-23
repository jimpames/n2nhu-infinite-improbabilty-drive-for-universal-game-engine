"""
N2NHU Infinite Improbability Drive - World Content Enricher
============================================================
v3 - Two-step prompting strategy + bulletproof output cleaner.

THE v2 PROBLEM:
  Llama ignores "output data lines ONLY" and writes:
  "Here are 12 objects: here | MRE Pack | ..."
  The preamble and data are on the SAME LINE.
  The cleaner skips the whole line, so the data is lost.

THE v3 FIX - Two-Step Prompting:
  Step 1 - Discovery (simple CSV question):
    "Name 12 objects you would find at MASH 4077th.
     Return as a comma-separated list only."
    Llama: "surgical kit, morphine, swamp still, ..."

  Step 2 - Structured data (anchored to Step 1 names):
    "For each of these objects from MASH 4077th:
     surgical kit, morphine, swamp still, ...
     Create one pipe-delimited game entry per object."
    Llama cannot drift to fantasy items because we feed
    the real names back in as explicit anchors.

WHY THIS WORKS:
  - Step 1 is a simple question Llama answers accurately
  - Step 2 uses those answers to ground the structured output
  - Two small focused prompts beat one complex prompt every time
  - Even if Step 2 formatting drifts, the names stay thematic

Also fixes same-line preamble bug: if "Here are objects: id | name |..."
appears, the data after the colon is rescued instead of discarded.

N2NHU Labs for Applied Artificial Intelligence
"""

import configparser
import os
import re
import random
from typing import List, Dict, Optional
from llm_providers import build_provider_chain, ProviderChain


# ── Debug flag ────────────────────────────────────────────────
DEBUG = os.environ.get('N2NHU_DEBUG', '0') == '1'

def _debug(label: str, text: str):
    if DEBUG:
        print(f'\n{"="*60}')
        print(f'  DEBUG [{label}]:')
        print(text[:3000])
        print(f'{"="*60}\n')


# ── Step 0: Context Discovery (anchors Steps 1 & 2) ───────────
# Same two-step pattern as room naming:
# First ask WHAT KIND of world this is, then ask for specific items.
# Prevents Llama from defaulting to generic military/spy templates
# when it doesn't recognise the world name.

OBJECTS_CONTEXT_PROMPT = (
    "What kinds of objects, props, and items would you typically find "
    "in {world_name}? Think about the actual setting, time period, and "
    "characters. Name the general categories only.\n"
    "Examples:\n"
    "- MASH 4077th -> surgical tools, dog tags, army rations, jeep parts, still\n"
    "- BEVERLY HILLBILLIES -> moonshine jug, shotgun, overalls, fishing pole, corn pone\n"
    "- GET SMART -> shoe phone, exploding pen, disguise kit, KAOS badge\n"
    "- HOGAN'S HEROES -> forged papers, tunnel map, German uniform, radio transmitter\n"
    "Give 6-10 category examples for {world_name}. "
    "Return ONLY a comma-separated list."
)

# ── Step 1: Discovery Prompts (anchored to Step 0 context) ────

OBJECTS_DISCOVERY = (
    "Name exactly {count} specific objects, items, or props from {world_name} "
    "({world_context}).\n"
    "Be specific and thematic - use real prop names from this setting.\n"
    "Return ONLY a comma-separated list. No descriptions, no numbers, no explanations.\n"
    "Example for {world_name}: {csv_example}"
)

SPRITES_DISCOVERY = (
    "Name exactly {count} characters from {world_name}.\n"
    "Include the actual cast members and recurring figures from this setting.\n"
    "Return ONLY a comma-separated list of character names. No descriptions, no numbers.\n"
    "Example for {world_name}: {csv_sprite_example}"
)

# ── Step 1b: Sprite Hallucination Challenge ────────────────────
# Llama sometimes invents characters when it runs out of real cast members.
# (e.g. "Monty Walsh" for STAR TREK, "Mrs. Lurch" for GILLIGANS ISLAND)
# Challenge step: verify every name before committing to Step 2.

SPRITES_CHALLENGE_PROMPT = (
    "From this list of characters, remove any that do NOT actually appear "
    "in {world_name}. Keep only real, canonical characters.\n\n"
    "Characters to verify:\n{character_names}\n\n"
    "Examples of invented (wrong) characters to remove:\n"
    "- STAR TREK: 'Monty Walsh' (not a real character - remove)\n"
    "- GILLIGANS ISLAND: 'Mrs. Lurch' (from Addams Family - remove)\n"
    "- MASH 4077th: 'General Flagg Smith' (invented name - remove)\n\n"
    "If a character IS real, keep them exactly as written.\n"
    "If the list has too few after removal, add real {world_name} characters "
    "to reach {count} total.\n\n"
    "Return ONLY a comma-separated list of {count} verified character names. "
    "No explanations."
)

# ── Step 2: Structured Prompts (anchored to Step 1 names) ────

OBJECTS_STRUCTURED = (
    "You are making a text adventure game set in {world_name}.\n\n"
    "Create a pipe-delimited game entry for EACH of these {count} objects:\n"
    "{object_names}\n\n"
    "One line per object. Format: id | name | takeable | weapon | consumable | wearable | damage | health | room | description\n\n"
    "Rules:\n"
    "- id: lowercase_with_underscores matching the object name\n"
    "- takeable/weapon/consumable/wearable: true or false\n"
    "- damage: 0-25 (0 unless it is a weapon)\n"
    "- health: 0-50 (0 unless it restores health)\n"
    "- room: one of these exact IDs: {room_ids}\n"
    "- description: one vivid sentence fitting {world_name}\n\n"
    "Example line:\n"
    "{example}\n\n"
    "Output the {count} pipe-delimited lines. Nothing else."
)

SPRITES_STRUCTURED = (
    "You are making a text adventure game set in {world_name}.\n\n"
    "Create a pipe-delimited game entry for EACH of these {count} characters:\n"
    "{character_names}\n\n"
    "One line per character. Format: id | name | role | aggression | health | damage | room | description\n\n"
    "Rules:\n"
    "- id: lowercase_with_underscores matching the character name\n"
    "- role: ally OR neutral OR villain OR boss OR guard\n"
    "- aggression: 0.0-1.0 (0.05=friendly ally, 0.9=hostile enemy)\n"
    "- health: 30-150\n"
    "- damage: 5-40\n"
    "- room: one of these exact IDs: {room_ids}\n"
    "- description: one sentence capturing their personality in {world_name}\n\n"
    "Example line:\n"
    "{example}\n\n"
    "Output the {count} pipe-delimited lines. Nothing else."
)

TRANSFORMS_PROMPT = (
    "You are making a text adventure game set in {world_name}.\n\n"
    "Create {count} object interactions using these object IDs: {object_ids}\n\n"
    "One line per interaction. Format: id | object_id | turns | new_state | message\n\n"
    "Rules:\n"
    "- id: snake_case action name (e.g. perform_surgery, tune_radio)\n"
    "- object_id: MUST exactly match one of the object IDs listed above\n"
    "- turns: 1, 2, or 3\n"
    "- new_state: result state (used, consumed, worn, activated, armed, cast, etc)\n"
    "- message: 1-2 sentences in the voice and tone of {world_name}\n\n"
    "Example line:\n"
    "{example}\n\n"
    "Output the {count} pipe-delimited lines. Nothing else."
)


# ── World examples ────────────────────────────────────────────

# ── Format Anchor ─────────────────────────────────────────────
# WORLD_EXAMPLES removed. WorldKnowledgeInterview provides all
# world-specific context (characters, object categories) at runtime.
# This single generic example shows Llama the pipe-delimited format only.
# Structure anchor — content comes from the interview.

_FORMAT_EXAMPLE = {
    'objects':    "ancient_key | Ancient Key | true | false | false | false | 0 | 0 | entrance | A heavy iron key whose purpose has been forgotten by everyone except the lock it was made for.",
    'sprites':    "mysterious_stranger | The Stranger | neutral | 0.30 | 60 | 10 | entrance | A figure who knows more than they say and says more than they should.",
    'transforms': "use_key | ancient_key | 1 | used | The lock recognizes the key. Something closed is now open.",
}


def _safe_id(name: str) -> str:
    s = re.sub(r"['\"]", '', name.lower().strip())
    s = re.sub(r'[^a-z0-9]+', '_', s)
    return s.strip('_')[:40] or 'item'

def _bool_val(val: str) -> bool:
    return str(val).strip().lower() in ('true', 'yes', '1', 't', 'y')

def _int_val(val: str, default: int = 0) -> int:
    try:
        return int(re.sub(r'[^\d]', '', str(val)) or str(default))
    except Exception:
        return default

def _float_val(val: str, default: float = 0.0) -> float:
    try:
        m = re.search(r'[\d.]+', str(val))
        return float(m.group()) if m else default
    except Exception:
        return default


# ── CSV name extractor (Step 1 response parser) ───────────────

def _parse_csv_names(text: str) -> List[str]:
    """
    Extract a clean list of names from a CSV response.
    Handles Llama quirks: preamble, numbered lists, bullets, multi-line.
    """
    text = re.sub(r'```[a-z]*\n?|```', '', text)

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    csv_line = text

    # Find the line with the most commas - that is the CSV
    if len(lines) > 1:
        best = max(lines, key=lambda l: l.count(','))
        if best.count(',') >= 2:
            csv_line = best

    # Strip any inline preamble before the actual names
    # e.g. "Here are 12 objects: surgical kit, morphine, ..."
    csv_line = re.sub(r'^[^:]+:\s*', '', csv_line)

    raw = re.split(r'[,\n]', csv_line)
    names = []
    for item in raw:
        item = item.strip()
        item = re.sub(r'^\d+[\.\)]\s*', '', item)
        item = re.sub(r'^[-*\u2022]\s*', '', item)
        item = item.strip('"\'')
        # Sanitise: strip any remaining quotes and embedded comma fragments
        # e.g. 'Wanted poster for "The Kid' -> 'Wanted poster for The Kid'
        item = item.replace('"', '').replace("'", '').strip()
        if item and 1 < len(item) < 60:
            names.append(item)

    return names


# ── Output cleaner v3 (fixes same-line preamble+data bug) ────

def _clean_llm_output(text: str) -> str:
    """
    Strip preamble/postamble. Rescue data that appears on the same
    line as preamble: "Here are the objects: id | name | ..."
    """
    text = re.sub(r'```[a-z]*\n?|```', '', text)

    PREAMBLE = [
        r'^here (are|is)',
        r'^the following',
        r'^below (is|are)',
        r"^i'?ve? (created|generated|made|listed)",
        r'^sure[,!]?\s',
        r'^note[:\s]',
        r'^please note',
        r'^these are',
        r'^output[:\s]',
        r'^result[:\s]',
        r'^---+$', r'^===+$',
        r'^\*\*[^|]',
        r'^#+ ',
    ]
    POSTAMBLE = [
        r'^i hope (this|these)',
        r'^let me know',
        r'^feel free',
        r'^note that',
        r'^please (let|feel)',
        r'^enjoy',
        r'^hope this helps',
    ]

    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue

        if re.search(r'\bobject_id\b|\bsprite_id\b|\btransform_id\b|\bdisplay_name\b', line.lower()):
            continue

        is_pre  = any(re.match(p, line.lower()) for p in PREAMBLE)
        is_post = any(re.match(p, line.lower()) for p in POSTAMBLE)

        if is_post:
            continue

        if is_pre:
            # v3 FIX: rescue data after colon on the same line
            if '|' in line:
                colon_pos = line.find(':')
                pipe_pos  = line.find('|')
                if colon_pos != -1 and colon_pos < pipe_pos:
                    candidate = line[colon_pos + 1:].strip()
                else:
                    parts = line[:pipe_pos].split()
                    candidate = (parts[-1] + line[pipe_pos:]) if parts else ''
                if candidate and candidate.count('|') >= 3:
                    lines.append(candidate)
            continue

        lines.append(line)

    return '\n'.join(lines)


# ── Multi-format line splitter ────────────────────────────────

def _split_line(line: str, max_fields: int = 10) -> List[str]:
    """
    Split a pipe-delimited LLM output line into fields.
    Uses maxsplit so the final field (description) absorbs any
    commas or pipes within it rather than being split further.
    """
    line = re.sub(r'^\d+[\.\)\-]\s*', '', line).strip()
    line = re.sub(r'^[-*\u2022]\s*', '', line).strip()

    # Pipe separator — preferred, use maxsplit to protect description field
    if '|' in line:
        parts = [p.strip() for p in line.split('|', max_fields - 1)]
        if len(parts) >= 4:
            return parts

    # Semicolon fallback
    if ';' in line:
        parts = [p.strip() for p in line.split(';', max_fields - 1)]
        if len(parts) >= 4:
            return parts

    # Tab fallback
    if '\t' in line:
        parts = [p.strip() for p in line.split('\t', max_fields - 1)]
        if len(parts) >= 4:
            return parts

    # Comma fallback — only if enough commas and no risk of description corruption
    # Require at least 7 commas (9-field object line minimum) before trusting it
    if ',' in line and line.count(',') >= 7:
        parts = [p.strip() for p in line.split(',', max_fields - 1)]
        if len(parts) >= 4:
            return parts

    return []


# ── Name sanitiser — strips embedded commas/quotes from Step 1 names ─
def _sanitise_name(name: str) -> str:
    """
    Clean a single object/sprite name coming out of Step 1 CSV parsing.
    Llama sometimes wraps names in quotes or includes commas within a name
    e.g. 'Wanted poster for "The Kid'  or  'Gold nuggets, leather pouch'
    We strip the quotes and remove any embedded comma fragments.
    """
    # Remove all quote characters
    name = name.replace('"', '').replace("'", '').strip()
    # If a comma survived (means the name itself had an embedded comma),
    # take only the part before the comma — it's the cleaner label
    if ',' in name:
        name = name.split(',')[0].strip()
    return name.strip()


# ── Object Parser ─────────────────────────────────────────────

def _clean_object_name(name: str) -> str:
    """
    Clean LLM-generated object names:
    - Removes slash-duplicated segments: "Ship's Console/Console Interface" 
      -> "Ship's Console Interface"
    - Collapses repeated adjacent words: "Views Screen Monitor" -> "Viewscreen Monitor"
    - Strips leading "Ship's" redundancy when it adds noise
    """
    import re as _re
    # Handle slash patterns: "A/A B" -> "A B",  "Console/Console Interface" -> "Console Interface"
    if '/' in name:
        parts = name.split('/')
        # Take the longer part (usually has more context)
        name = max(parts, key=len).strip()

    # Collapse repeated adjacent words (case-insensitive): "Console Console" -> "Console"
    words = name.split()
    deduped = []
    for w in words:
        if not deduped or w.lower() != deduped[-1].lower():
            deduped.append(w)
    name = ' '.join(deduped)

    # Cap at 5 words to prevent runaway names
    name = ' '.join(name.split()[:5])

    return name.strip()


def parse_objects(llm_output: str, room_ids: List[str],
                  world_name: str) -> List[Dict]:
    _debug('RAW OBJECTS', llm_output)
    cleaned = _clean_llm_output(llm_output)
    _debug('CLEANED OBJECTS', cleaned)

    objects  = []
    seen_ids = set()

    for line in cleaned.split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = _split_line(line)
        if len(parts) < 3:
            continue
        try:
            raw_id     = parts[0]
            # Reject preamble lines that leaked into ID field:
            # e.g. "Here are the objects" -> "here_are_the_objects"
            # Heuristic: real IDs are short snake_case, preamble has spaces/many words
            if len(raw_id.split()) > 3 or len(raw_id) > 40:
                continue
            name       = parts[1] if len(parts) > 1 else raw_id
            # Clean doubled names: "Console/Console Interface" -> "Console Interface"
            name = _clean_object_name(name)
            obj_id     = _safe_id(raw_id) or _safe_id(name)
            if not obj_id or len(obj_id) < 2:
                continue

            takeable   = _bool_val(parts[2]) if len(parts) > 2 else True
            weapon     = _bool_val(parts[3]) if len(parts) > 3 else False
            consumable = _bool_val(parts[4]) if len(parts) > 4 else False
            wearable   = _bool_val(parts[5]) if len(parts) > 5 else False
            damage     = _int_val(parts[6])  if len(parts) > 6 else 0
            health_r   = _int_val(parts[7])  if len(parts) > 7 else 0
            location   = parts[8].strip()    if len(parts) > 8 else ''
            desc       = parts[9].strip()    if len(parts) > 9 else f'A {name}.'

            if location not in room_ids:
                location = random.choice(room_ids)

            base = obj_id; n = 1
            while obj_id in seen_ids:
                obj_id = f'{base}_{n}'; n += 1
            seen_ids.add(obj_id)

            verbs = ['take', 'drop', 'examine', 'use']
            if weapon:   verbs.append('attack')
            if wearable: verbs.append('wear')

            objects.append({
                'id':           obj_id,
                'name':         name,
                'description':  desc.replace('%', '%%'),
                'location':     location,
                'takeable':     str(takeable).lower(),
                'weapon':       str(weapon).lower(),
                'damage':       str(damage),
                'consumable':   str(consumable).lower(),
                'health_restore': str(health_r),
                'wearable':     str(wearable).lower(),
                'valid_verbs':  ', '.join(verbs),
            })
        except Exception as e:
            if DEBUG:
                print(f'  obj parse err: {line!r} -> {e}')
    return objects


# ── Sprite Parser ─────────────────────────────────────────────

def parse_sprites(llm_output: str, room_ids: List[str]) -> List[Dict]:
    _debug('RAW SPRITES', llm_output)
    cleaned = _clean_llm_output(llm_output)
    _debug('CLEANED SPRITES', cleaned)

    sprites  = []
    seen_ids = set()
    valid_roles = {'ally', 'neutral', 'villain', 'boss', 'guard'}

    for line in cleaned.split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = _split_line(line)
        if len(parts) < 4:
            continue
        try:
            raw_id     = parts[0]
            # Reject preamble lines: "Here are the characters" has >3 words
            if len(raw_id.split()) > 3 or len(raw_id) > 40:
                continue
            name       = parts[1] if len(parts) > 1 else raw_id
            sprite_id  = _safe_id(raw_id) or _safe_id(name)
            if not sprite_id or len(sprite_id) < 2:
                continue

            role       = parts[2].strip().lower() if len(parts) > 2 else 'neutral'
            aggression = _float_val(parts[3], 0.3) if len(parts) > 3 else 0.3
            health     = _int_val(parts[4], 60)    if len(parts) > 4 else 60
            damage     = _int_val(parts[5], 10)    if len(parts) > 5 else 10
            spawn_room = parts[6].strip()           if len(parts) > 6 else ''
            desc       = parts[7].strip()           if len(parts) > 7 else f'{name}.'

            if role not in valid_roles:
                role = 'neutral'
            if spawn_room not in room_ids:
                spawn_room = random.choice(room_ids)
            aggression = max(0.0, min(1.0, aggression))
            # Sanity caps — catches LLM typos like 225 instead of 25
            health     = max(10,  min(300, health))
            damage     = max(0,   min(99,  damage))

            base = sprite_id; n = 1
            while sprite_id in seen_ids:
                sprite_id = f'{base}_{n}'; n += 1
            seen_ids.add(sprite_id)

            behavior_map = {
                'ally':    'ally_support',
                'neutral': 'neutral_npc',
                'villain': 'aggressive_patrol',
                'boss':    'aggressive_patrol',
                'guard':   'patrol_basic',
            }
            sprites.append({
                'id':          sprite_id,
                'name':        name,
                'description': desc.replace('%', '%%'),
                'role':        role,
                'aggression':  f'{aggression:.2f}',
                'health':      str(health),
                'damage':      str(damage),
                'spawn_rooms': spawn_room,
                'spawn_chance': '0.05',
                'ai_behavior': behavior_map.get(role, 'neutral_npc'),
                'can_pickup':  'true',
                'loot_on_death': '',
            })
        except Exception as e:
            if DEBUG:
                print(f'  sprite parse err: {line!r} -> {e}')
    return sprites


# ── Transform Parser ──────────────────────────────────────────

def parse_transforms(llm_output: str, object_ids: List[str]) -> List[Dict]:
    _debug('RAW TRANSFORMS', llm_output)
    cleaned = _clean_llm_output(llm_output)

    transforms = []
    seen_ids   = set()

    for line in cleaned.split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = _split_line(line)
        if len(parts) < 4:
            continue
        try:
            t_id      = _safe_id(parts[0])
            object_id = parts[1].strip() if len(parts) > 1 else ''
            turns     = _int_val(parts[2], 1)
            new_state = parts[3].strip() if len(parts) > 3 else 'used'
            message   = parts[4].strip() if len(parts) > 4 else 'You use the item.'

            if object_id not in object_ids:
                matched = next(
                    (o for o in object_ids if object_id in o or o in object_id),
                    None)
                object_id = matched or (random.choice(object_ids) if object_ids else '')
            if not object_id:
                continue

            if not t_id:
                t_id = f'use_{object_id}'

            base = t_id; n = 1
            while t_id in seen_ids:
                t_id = f'{base}_{n}'; n += 1
            seen_ids.add(t_id)

            message = (message
                       .replace('\u2014', ' - ')
                       .replace('--', ' - ')
                       .replace('%', '%%'))

            transforms.append({
                'id':             t_id,
                'object_id':      object_id,
                'state':          'normal',
                'turns_required': str(max(1, min(5, turns))),
                'new_state':      new_state,
                'message':        message,
            })
        except Exception as e:
            if DEBUG:
                print(f'  transform parse err: {line!r} -> {e}')
    return transforms


# ── Template fallbacks (always produce playable output) ──────

def _names_to_minimal_objects(names: List[str], room_ids: List[str],
                               world_name: str) -> List[Dict]:
    """
    Last-resort fallback: Step 2 structured parse failed but we have
    Step 1 names. Build minimal valid objects directly from those names
    rather than falling back to generic military templates.
    The names are world-correct — we keep them and generate sane defaults.
    """
    result = []
    for name in names:
        obj_id = _safe_id(name)
        if not obj_id:
            continue
        result.append({
            'id':             obj_id,
            'name':           name,
            'description':    f'{name} — a notable item found in {world_name}.',
            'location':       random.choice(room_ids),
            'takeable':       'true',
            'weapon':         'false',
            'damage':         '0',
            'consumable':     'false',
            'health_restore': '0',
            'wearable':       'false',
            'valid_verbs':    'take, drop, examine, use',
        })
    return result


def _names_to_minimal_sprites(names: List[str], room_ids: List[str],
                               world_name: str) -> List[Dict]:
    """
    Last-resort fallback: Step 2 structured parse failed but we have
    Step 1 names. Build minimal valid sprites from those names.
    Far better than generic 'World Character 1, Character 2...'
    """
    roles = ['ally', 'neutral', 'villain', 'guard', 'boss']
    agg   = {'ally': 0.05, 'neutral': 0.3, 'villain': 0.7,
             'guard': 0.5, 'boss': 0.9}
    beh   = {'ally': 'ally_support', 'neutral': 'neutral_npc',
             'villain': 'aggressive_patrol', 'guard': 'patrol_basic',
             'boss': 'aggressive_patrol'}
    result = []
    for i, name in enumerate(names):
        spr_id = _safe_id(name)
        if not spr_id:
            continue
        role = roles[i % len(roles)]
        result.append({
            'id':            spr_id,
            'name':          name,
            'description':   f'{name}, a character from {world_name}.',
            'role':          role,
            'aggression':    f'{agg[role]:.2f}',
            'health':        '80',
            'damage':        '12',
            'spawn_rooms':   random.choice(room_ids),
            'spawn_chance':  '0.05',
            'ai_behavior':   beh[role],
            'can_pickup':    'true',
            'loot_on_death': '',
        })
    return result


# ── INI Writer ────────────────────────────────────────────────

def _write_ini(items: List[Dict], path: str, world_name: str, label: str):
    config = configparser.RawConfigParser()
    for item in items:
        sec = item['id']
        if config.has_section(sec):
            sec = f"{sec}_x"
        config.add_section(sec)
        for key, val in item.items():
            if key != 'id':
                config.set(sec, key, str(val))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f'# {label} - {world_name}\n')
        f.write(f'# Enriched by N2NHU Infinite Improbability Drive v3\n')
        f.write(f'# Count: {len(items)}\n\n')
        config.write(f)


# ── Provider chain patch (applied on import) ─────────────────

def _patch_provider_chain():
    import requests
    from llm_providers import (ProviderChain, GPT4AllProvider,
                                ClaudeProvider, HuggingFaceProvider,
                                TemplateProvider)

    def generate_raw(self, prompt: str) -> str:
        for provider in self.providers:
            if not provider.is_available():
                continue
            result = provider._generate_raw(prompt)
            if result and len(result.strip()) > 10:
                self._last_provider_used = provider.name
                return result
        return ''
    ProviderChain.generate_raw = generate_raw

    def gpt4all_raw(self, prompt: str):
        try:
            r = requests.post(
                f'{self.base_url}/chat/completions',
                json={'model': self.model,
                      'messages': [{'role': 'user', 'content': prompt}],
                      'max_tokens': 1200, 'temperature': 0.7},
                timeout=self.timeout)
            r.raise_for_status()
            return r.json()['choices'][0]['message']['content'].strip()
        except Exception as e:
            if DEBUG:
                print(f'  GPT4All error: {e}')
            return None

    def claude_raw(self, prompt: str):
        if not self.is_available():
            return None
        try:
            r = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={'x-api-key': self.api_key,
                         'anthropic-version': '2023-06-01',
                         'content-type': 'application/json'},
                json={'model': self.model, 'max_tokens': 1200,
                      'messages': [{'role': 'user', 'content': prompt}]},
                timeout=30)
            r.raise_for_status()
            return r.json()['content'][0]['text'].strip()
        except Exception as e:
            if DEBUG:
                print(f'  Claude error: {e}')
            return None

    def hf_raw(self, prompt: str):
        if not self.is_available():
            return None
        try:
            r = requests.post(
                f'https://api-inference.huggingface.co/models/{self.model}',
                headers={'Authorization': f'Bearer {self.api_key}'},
                json={'inputs': prompt,
                      'parameters': {'max_new_tokens': 1200,
                                     'temperature': 0.7,
                                     'return_full_text': False}},
                timeout=60)
            r.raise_for_status()
            data = r.json()
            text = data[0].get('generated_text', '') if isinstance(data, list) else ''
            return text.replace(prompt, '').strip() if prompt in text else text
        except Exception as e:
            if DEBUG:
                print(f'  HuggingFace error: {e}')
            return None

    def tmpl_raw(self, prompt: str):
        return None

    GPT4AllProvider._generate_raw     = gpt4all_raw
    ClaudeProvider._generate_raw      = claude_raw
    HuggingFaceProvider._generate_raw = hf_raw
    TemplateProvider._generate_raw    = tmpl_raw

_patch_provider_chain()


# ── Master Enricher ───────────────────────────────────────────

class WorldContentEnricher:

    def __init__(self, provider_chain: ProviderChain):
        self.chain = provider_chain

    def _step1_object_names(self, world_name: str, count: int,
                             ctx_csv: str = '') -> List[str]:

        # Step 0: Discover what KIND of world this is so Step 1 is anchored
        ctx_prompt = OBJECTS_CONTEXT_PROMPT.format(world_name=world_name)
        print(f'   Step 0: What kinds of objects exist in {world_name!r}?')
        raw_ctx = self.chain.generate_raw(ctx_prompt) or ''
        world_context = _parse_csv_names(raw_ctx)
        world_context = ', '.join(world_context[:8]) if world_context else world_name
        print(f'   Step 0: Context -> {world_context[:80]}...')

        # Step 1: Ask for specific names anchored to the context
        prompt = OBJECTS_DISCOVERY.format(
            count         = count,
            world_name    = world_name,
            world_context = world_context,
            csv_example   = ctx_csv,
        )
        print(f'   Step 1: Asking Llama to name {count} objects in {world_name}...')
        raw   = self.chain.generate_raw(prompt)
        _debug('OBJECT NAMES RAW', raw or '')
        names = _parse_csv_names(raw) if raw else []
        preview = ', '.join(names[:5]) + ('...' if len(names) > 5 else '')
        print(f'   Step 1: {len(names)} names -> {preview}')
        return names

    def _step1_sprite_names(self, world_name: str, count: int,
                             ctx_chars: str = '') -> List[str]:
        # Step 1: Initial character discovery
        prompt = SPRITES_DISCOVERY.format(
            count              = count,
            world_name         = world_name,
            csv_sprite_example = ctx_chars,
        )
        print(f'   Step 1: Asking Llama to name {count} characters in {world_name}...')
        raw   = self.chain.generate_raw(prompt)
        _debug('SPRITE NAMES RAW', raw or '')
        names = _parse_csv_names(raw) if raw else []
        preview = ', '.join(names[:5]) + ('...' if len(names) > 5 else '')
        print(f'   Step 1: {len(names)} names -> {preview}')

        if not names:
            return names

        # Step 1b: Challenge — verify every name is a real character
        # Catches hallucinated characters like "Monty Walsh" (STAR TREK)
        # or "Mrs. Lurch" (GILLIGANS ISLAND)
        names_str = ', '.join(names)
        challenge = SPRITES_CHALLENGE_PROMPT.format(
            world_name       = world_name,
            character_names  = names_str,
            count            = count,
        )
        print(f'   Step 1b: Verifying {len(names)} characters are real cast members...')
        raw1b = self.chain.generate_raw(challenge) or ''
        if raw1b:
            verified = _parse_csv_names(raw1b)
            # Accept if we got at least 1 real name back (was too conservative at count//2)
            # Llama often returns fewer names if it correctly removed hallucinations
            if verified and len(verified) >= 1:
                removed = [n for n in names if n not in verified]
                added   = [n for n in verified if n not in names]
                if removed:
                    print(f'   Step 1b: Removed hallucinated: {", ".join(removed)}')
                if added:
                    print(f'   Step 1b: Added real cast: {", ".join(added)}')
                if not removed and not added:
                    print(f'   Step 1b: All characters verified ✅')
                names = verified
            else:
                print(f'   Step 1b: Challenge inconclusive — keeping original list')

        return names


    def enrich_all(self, output_dir: str, world_name: str,
                   object_count: int = 10, sprite_count: int = 6,
                   transform_count: int = 5,
                   progress_cb=None,
                   world_context=None) -> dict:
        """
        Enrich objects, sprites, and transformations.
        If world_context (from WorldKnowledgeInterview) is provided,
        object/sprite discovery steps are anchored to validated facts
        instead of doing blind LLM discovery.
        """

        objects_path    = os.path.join(output_dir, 'objects.ini')
        sprites_path    = os.path.join(output_dir, 'sprites.ini')
        transforms_path = os.path.join(output_dir, 'transformations.ini')
        rooms_path      = os.path.join(output_dir, 'rooms.ini')

        rooms_cfg = configparser.RawConfigParser()
        rooms_cfg.read(rooms_path, encoding='utf-8')
        room_ids = rooms_cfg.sections()
        if not room_ids:
            return {'error': 'No rooms found'}

        # Context from interview anchors object/sprite discovery
        ctx_csv   = ''
        ctx_chars = ''
        if world_context and world_context.is_valid():
            if world_context.object_categories:
                ctx_csv = ', '.join(world_context.object_categories[:8])
                print(f'   Enricher: Object context from interview: {ctx_csv[:60]}...')
            if world_context.characters:
                ctx_chars = ', '.join(world_context.characters[:6])
                print(f'   Enricher: Characters from interview: {ctx_chars[:60]}...')

        results  = {}

        # ── Objects: two-step ─────────────────────────────────
        if progress_cb:
            progress_cb('Objects', 0, 1, 'Generating...', '')
        print(f'\n{"─"*50}')
        print(f'  Objects for {world_name}')
        print(f'{"─"*50}')

        obj_names = self._step1_object_names(world_name, object_count, ctx_csv)
        objects   = []

        if obj_names:
            names_str = '\n'.join(f'- {n}' for n in obj_names)
            prompt    = OBJECTS_STRUCTURED.format(
                world_name   = world_name,
                count        = len(obj_names),
                object_names = names_str,
                room_ids     = ', '.join(room_ids),
                example      = _FORMAT_EXAMPLE['objects'],
            )
            print(f'   Step 2: Building structured data for {len(obj_names)} objects...')
            raw     = self.chain.generate_raw(prompt)
            objects = parse_objects(raw, room_ids, world_name) if raw else []

        if not objects:
            if obj_names:
                print(f'   Step 2 parse failed — building from Step 1 names')
                objects = _names_to_minimal_objects(obj_names, room_ids, world_name)
            else:
                print(f'   WARNING: No names and no parse — world will have no objects')

        _write_ini(objects, objects_path, world_name, 'Object Definitions')
        print(f'   OK: {len(objects)} objects written')
        results['objects'] = len(objects)
        if progress_cb:
            progress_cb('Objects', 1, 1, 'Complete', str(len(objects)))

        # ── Sprites: two-step ─────────────────────────────────
        if progress_cb:
            progress_cb('Sprites', 0, 1, 'Generating...', '')
        print(f'\n{"─"*50}')
        print(f'  Characters for {world_name}')
        print(f'{"─"*50}')

        spr_names = self._step1_sprite_names(world_name, sprite_count, ctx_chars)
        sprites   = []

        if spr_names:
            names_str = '\n'.join(f'- {n}' for n in spr_names)
            prompt    = SPRITES_STRUCTURED.format(
                world_name      = world_name,
                count           = len(spr_names),
                character_names = names_str,
                room_ids        = ', '.join(room_ids),
                example         = _FORMAT_EXAMPLE['sprites'],
            )
            print(f'   Step 2: Building structured data for {len(spr_names)} characters...')
            raw     = self.chain.generate_raw(prompt)
            sprites = parse_sprites(raw, room_ids) if raw else []

        if not sprites:
            if spr_names:
                print(f'   Step 2 parse failed — building from Step 1 names')
                sprites = _names_to_minimal_sprites(spr_names, room_ids, world_name)
            else:
                print(f'   WARNING: No names and no parse — world will have no characters')

        _write_ini(sprites, sprites_path, world_name, 'Sprite Definitions')
        print(f'   OK: {len(sprites)} characters written')
        results['sprites'] = len(sprites)
        if progress_cb:
            progress_cb('Sprites', 1, 1, 'Complete', str(len(sprites)))

        # ── Transforms: single-step (object IDs now known) ────
        object_ids = [o['id'] for o in objects]
        if os.path.exists(objects_path):
            ec = configparser.RawConfigParser()
            ec.read(objects_path, encoding='utf-8')
            for s in ec.sections():
                if s not in object_ids:
                    object_ids.append(s)

        if progress_cb:
            progress_cb('Transforms', 0, 1, 'Generating...', '')
        print(f'\n{"─"*50}')
        print(f'  Transformations for {world_name}')
        print(f'{"─"*50}')

        prompt = TRANSFORMS_PROMPT.format(
            world_name = world_name,
            count      = transform_count,
            object_ids = ', '.join(object_ids[:15]),
            example    = _FORMAT_EXAMPLE['transforms'],
        )
        raw        = self.chain.generate_raw(prompt)
        transforms = parse_transforms(raw, object_ids) if raw else []

        if not transforms:
            print(f'   WARNING: No transforms parsed')

        _write_ini(transforms, transforms_path, world_name,
                   'Transformation Matrices')
        print(f'   OK: {len(transforms)} transformations written')
        results['transforms'] = len(transforms)
        if progress_cb:
            progress_cb('Transforms', 1, 1, 'Complete', str(len(transforms)))

        return results


# ── CLI ───────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    if '--debug' in sys.argv:
        os.environ['N2NHU_DEBUG'] = '1'
        import content_enricher as _ce
        _ce.DEBUG = True

    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    output_dir = args[0] if len(args) > 0 else './generated_world'
    world_name = args[1] if len(args) > 1 else 'MASH 4077'

    chain = build_provider_chain({
        'gpt4all_host':  'localhost',
        'gpt4all_port':  '4891',
        'gpt4all_model': 'Llama 3 8B Instruct',
    })
    print(chain.detect_and_report())

    enricher = WorldContentEnricher(chain)
    results  = enricher.enrich_all(output_dir, world_name)

    print(f'\n{"="*50}')
    print(f'Objects: {results.get("objects", 0)}  '
          f'Sprites: {results.get("sprites", 0)}  '
          f'Transforms: {results.get("transforms", 0)}')
