"""
N2NHU Infinite Improbability Drive - LLM Room Namer
====================================================
Two-step room name discovery using Jim's prompting strategy.

THE PROBLEM:
  The theme engine has suggested_room_prefixes per theme, but
  these are generic buckets. "THREE'S COMPANY" maps to SITCOM
  which gives: Living Room, Kitchen, Front Stoop, Diner...
  That's better than Chamber/Zone/Space but still not
  specifically Three's Company.

JIM'S TWO-STEP FIX:
  Step 1 — Setting discovery:
    "What is the usual setting of THREE'S COMPANY?"
    → Llama: "APARTMENT"

  Step 2 — Room name generation (anchored to Step 1):
    "What are 10 room names you would find in a
     THREE'S COMPANY APARTMENT?"
    → Llama: "Jack's Bedroom, Janet's Bedroom, Living Room,
              Kitchen, Hallway, Mr. Roper's Office,
              Bathroom, Front Door, Patio, Landlord's Apartment"

WHY THIS WORKS:
  - Step 1 grounds Step 2 in the actual physical setting
  - Step 2 uses both the world name AND the setting word
    so Llama generates location-specific names not just
    generic theme names
  - "THREE'S COMPANY APARTMENT" triggers different knowledge
    than just "SITCOM" room names

EXAMPLES:
  "MASH 4077"      → Setting: MILITARY FIELD HOSPITAL
                   → Rooms: Operating Room, Recovery Ward,
                             The Swamp, Mess Hall, CO's Office...

  "Studio 54"      → Setting: DISCO NIGHTCLUB
                   → Rooms: Dance Floor, VIP Balcony, DJ Booth,
                             Back Room, Coat Check...

  "Chuck E. Cheese's" → Setting: KIDS PIZZA ARCADE
                      → Rooms: Arcade Room, Party Room,
                                Pizza Counter, Stage, Ticket Booth...

  "Barbie World"   → Setting: DREAM HOUSE
                   → Rooms: Dream Closet, Pink Bedroom,
                             Fashion Studio, Dream Kitchen...

N2NHU Labs for Applied Artificial Intelligence
"""

import re
import os
from typing import List, Optional

DEBUG = os.environ.get('N2NHU_DEBUG', '0') == '1'


# ── Step 1: Setting Discovery ─────────────────────────────────

SETTING_DISCOVERY_PROMPT = """\
What is the usual physical setting or location of: {world_name}

Examples of correct answers:
- THREE'S COMPANY          -> APARTMENT
- MASH 4077th              -> MILITARY FIELD HOSPITAL
- Studio 54                -> DISCO NIGHTCLUB
- Barbie World             -> DREAM HOUSE
- Bewitched                -> SUBURBAN HOME
- Hogans Heroes            -> PRISONER OF WAR CAMP
- Area 51                  -> SECRET MILITARY BASE
- Cheers                   -> BAR
- Chuck E. Cheese's        -> KIDS PIZZA ARCADE
- Gilligan's Island        -> TROPICAL ISLAND
- The Flintstones          -> PREHISTORIC TOWN
- The Love Boat            -> CRUISE SHIP
- Fantasy Island           -> TROPICAL RESORT
- Green Acres              -> FARM

Return ONLY 1-4 words describing the physical setting. No explanation."""


# ── Step 2: Room Name Generation (anchored to Step 1) ─────────

ROOM_NAMES_PROMPT = """\
List exactly {count} room names or locations you would find in \
{world_name}, which is set in a {setting}.

Rules:
- Use the actual room names specific to {world_name} where known
- If character names are associated with rooms, include them
  (e.g. "Jack's Bedroom", "Mr. Roper's Office")
- Use the physical setting "{setting}" to guide your choices
- Names should be 1-4 words, suitable as room labels in a game
- Always include an entrance or front door equivalent

Example for THREE'S COMPANY (APARTMENT):
Living Room, Kitchen, Jack's Bedroom, Janet's Bedroom, Hallway, \
Bathroom, Mr. Roper's Office, Front Stoop, Patio, Chrissy's Room

Example for MASH 4077th (MILITARY FIELD HOSPITAL):
Operating Room, Recovery Ward, The Swamp, Mess Hall, \
CO's Office, Supply Depot, Infirmary, Motor Pool, \
Briefing Room, Entrance

Return ONLY a comma-separated list of {count} room names. \
No numbers, no explanations."""




# ── Step 1b: Setting Confirmation (binary YES/NO before any correction) ──
# Jim's design: "is a MARINE BASE where the scene is set for GOMER PYLE USMC?"
# Binary question first — only ask for a correction if Llama says NO.
# This prevents the old open-ended challenge from "correcting" correct answers
# like MARINE BASE -> SOUTH CAROLINA COAST.
#
# Loop: up to MAX_CONFIRM_ROUNDS of confirm/correct until stable or MAX reached.

SETTING_CONFIRM_PROMPT = """\
Yes or No: Is {raw_setting} the correct physical setting where \
{world_name} takes place?

Examples:
- Is MARINE BASE correct for GOMER PYLE USMC?       -> Yes
- Is JUNKYARD correct for SANFORD AND SON?           -> Yes
- Is FURNITURE FACTORY correct for SANFORD AND SON?  -> No
- Is NIGHTCLUB correct for BARNEY MILLER?            -> No
- Is POLICE PRECINCT correct for BARNEY MILLER?      -> Yes
- Is TROPICAL ISLAND correct for GILLIGANS ISLAND?   -> Yes
- Is APARTMENT correct for THREE'S COMPANY?          -> Yes

Answer ONLY Yes or No."""

SETTING_CORRECT_PROMPT = """\
{raw_setting} is NOT the correct setting for {world_name}.
What IS the correct 1-4 word physical setting where {world_name} takes place?

Examples of correct settings:
- SANFORD AND SON    -> JUNKYARD
- BARNEY MILLER      -> POLICE PRECINCT
- GOMER PYLE USMC   -> MARINE BASE
- GILLIGAN'S ISLAND  -> TROPICAL ISLAND
- MASH 4077th        -> MILITARY FIELD HOSPITAL
- HOGAN'S HEROES     -> PRISONER OF WAR CAMP
- GREEN ACRES        -> FARM

Return ONLY 1-4 words. No explanation."""

MAX_CONFIRM_ROUNDS = 2   # confirm → correct → re-confirm (at most)

# ── Response Cleaners ─────────────────────────────────────────

def _clean_setting(text: str) -> str:
    """Extract setting word(s) from LLM response."""
    text = text.strip()

    # Strip markdown
    text = re.sub(r'```[a-z]*\n?|```', '', text).strip()

    # Take first line only
    text = text.split('\n')[0].strip()

    # Strip ALL preamble patterns Llama uses
    preamble_patterns = [
        r'^(the\s+)?(setting|location|place|world|scene|genre)\s+(is|would be|of|for)[:\s]+',
        r'^(it is|that is|i would say|this is|sure[!,]?\s+this is)[:\s]+',
        r'^(sure[!,]?\s+(it is(\s+a)?|the\s+setting\s+is)?)\s*',
        r'^(sure[!,]?\s+)',
        r'^(well[,]?\s+)',
        r'^(the\s+answer\s+is)[:\s]+',
        r'^(most\s+probable[:\s]+)',
        r'^(correct\s+setting\s+is)[:\s]+',
        r'^(the\s+correct\s+setting\s+is)[:\s]+',
        r'^[a-z\s,!]+:\s+',   # catch-all: "word word word: ANSWER"
    ]
    for pat in preamble_patterns:
        text = re.sub(pat, '', text, flags=re.IGNORECASE).strip()

    # Strip leading articles (a, an, the)
    text = re.sub(r'^(a|an|the)\s+', '', text, flags=re.IGNORECASE).strip()

    # Remove trailing qualifiers like "(correct)" or "(not furniture factory)"
    text = re.sub(r'\s*\([^)]*\)\s*$', '', text).strip()

    # Remove trailing punctuation
    text = text.rstrip('.,!?')

    # Cap at 4 words
    words = text.split()
    text = ' '.join(words[:4])

    return text.upper().strip()


def _clean_room_names(text: str, count: int) -> List[str]:
    """
    Extract clean room names from LLM CSV response.
    Handles: preamble, numbered lists, bullets, multi-line.
    """
    # Strip markdown
    text = re.sub(r'```[a-z]*\n?|```', '', text)

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    csv_line = text

    # Find line with most commas — that is the CSV
    if len(lines) > 1:
        best = max(lines, key=lambda l: l.count(','))
        if best.count(',') >= 2:
            csv_line = best

    # Strip inline preamble before actual names
    # e.g. "Here are 10 rooms: Living Room, Kitchen, ..."
    csv_line = re.sub(r'^[^:]+:\s*', '', csv_line)

    raw = re.split(r'[,\n]', csv_line)
    names = []
    for item in raw:
        item = item.strip()
        item = re.sub(r'^\d+[\.\)]\s*', '', item)   # remove numbering
        item = re.sub(r'^[-*\u2022]\s*', '', item)   # remove bullets
        item = item.strip('"\'')
        if item and 2 < len(item) < 50:
            names.append(item)

    return names[:count]


# ── LLM Room Namer ────────────────────────────────────────────

class LLMRoomNamer:
    """
    Two-step LLM room name generator.
    Step 1: discover the physical setting of the world.
    Step 2: generate specific room names for that world+setting.
    Falls back to theme engine prefixes if LLM unavailable.
    """

    def __init__(self, provider_chain):
        self.chain = provider_chain
        self._last_setting = None
        self._last_method  = None

    @property
    def last_setting(self):
        return self._last_setting

    @property
    def last_method(self):
        return self._last_method

    def generate_names(self, world_name: str, count: int,
                       fallback_names: Optional[List[str]] = None,
                       world_context=None) -> List[str]:
        """
        Generate count room names for world_name using two-step LLM.
        If world_context is provided (from WorldKnowledgeInterview),
        setting discovery (Steps 1/1b) is skipped — context is truth.
        Returns fallback_names (or generic list) if LLM unavailable.
        """

        # ── Fast path: context already established by interview ─
        if world_context and world_context.setting:
            setting = world_context.setting
            print(f'   Room: Using interview context — setting={setting!r}')
            self._last_setting = setting
            self._last_method  = 'interview'
            # Jump straight to Step 2
            prompt2 = ROOM_NAMES_PROMPT.format(
                world_name = world_name,
                setting    = setting,
                count      = count,
            )
            # Enrich prompt with known characters if available
            if world_context.characters:
                char_hint = ', '.join(world_context.characters[:4])
                prompt2 = prompt2 + (
                    f'\n\nKnown characters in {world_name}: {char_hint}\n'
                    f'Include rooms named after these characters where appropriate.'
                )
            print(f'   Room Step 2: Naming {count} rooms for {world_name} ({setting})...')
            raw2 = ''
            try:
                raw2 = self.chain.generate_raw(prompt2) or ''
            except Exception:
                pass
            names = _clean_room_names(raw2, count) if raw2 else []
            if names:
                print(f'   Room Step 2: Got {len(names)} names -> {", ".join(names[:4])}...')
                return names
            return _apply_fallback(fallback_names, count)

        # ── Step 1: Discover setting ──────────────────────────
        prompt1 = SETTING_DISCOVERY_PROMPT.format(world_name=world_name)
        print(f'   Room Step 1: What is the setting of {world_name!r}?')

        raw1 = ''
        try:
            raw1 = self.chain.generate_raw(prompt1) or ''
        except Exception as e:
            if DEBUG:
                print(f'   Room Step 1 error: {e}')

        if DEBUG:
            print(f'   Room Step 1 raw: {raw1!r}')

        setting = _clean_setting(raw1) if raw1 else ''

        if not setting or len(setting) < 3:
            print(f'   Room Step 1: LLM unavailable — using fallback names')
            self._last_method  = 'fallback'
            self._last_setting = None
            return _apply_fallback(fallback_names, count)

        self._last_setting = setting
        print(f'   Room Step 1: {world_name} = {setting}')

        # ── Step 1b: Binary confirm/correct loop ──────────────
        # Jim's design: ask YES/NO first — "Is MARINE BASE correct for
        # GOMER PYLE USMC?" Only correct if Llama says NO.
        # Loop up to MAX_CONFIRM_ROUNDS to reach a stable confirmed answer.

        for round_num in range(1, MAX_CONFIRM_ROUNDS + 1):
            confirm_prompt = SETTING_CONFIRM_PROMPT.format(
                raw_setting = setting,
                world_name  = world_name,
            )
            print(f'   Room Step 1b (round {round_num}): '
                  f'Is {setting!r} correct for {world_name!r}?')
            raw_confirm = ''
            try:
                raw_confirm = self.chain.generate_raw(confirm_prompt) or ''
            except Exception:
                pass

            if not raw_confirm:
                print(f'   Room Step 1b: No response — keeping {setting!r}')
                break

            answer = raw_confirm.strip().lower()[:20]
            confirmed = answer.startswith('yes') or 'yes' in answer[:8]
            denied    = answer.startswith('no')  or answer[:8].strip() in ('no', 'no.')

            if confirmed:
                print(f'   Room Step 1b: Confirmed ✅ {setting!r}')
                break

            elif denied:
                # Ask for the correction
                correct_prompt = SETTING_CORRECT_PROMPT.format(
                    raw_setting = setting,
                    world_name  = world_name,
                )
                print(f'   Room Step 1b: LLM said NO — asking for correction...')
                raw_correct = ''
                try:
                    raw_correct = self.chain.generate_raw(correct_prompt) or ''
                except Exception:
                    pass

                if raw_correct:
                    corrected = _clean_setting(raw_correct)
                    if corrected and len(corrected) >= 3 and corrected != setting:
                        print(f'   Room Step 1b: Corrected {setting!r} -> {corrected!r}')
                        setting = corrected
                        # Loop continues — will re-confirm the new setting
                    else:
                        print(f'   Room Step 1b: Correction unclear — keeping {setting!r}')
                        break
                else:
                    print(f'   Room Step 1b: No correction — keeping {setting!r}')
                    break
            else:
                # Ambiguous response — keep what we have
                print(f'   Room Step 1b: Ambiguous response {answer!r} — keeping {setting!r}')
                break

        self._last_setting = setting

        # ── Step 2: Generate room names for world+setting ─────
        prompt2 = ROOM_NAMES_PROMPT.format(
            world_name = world_name,
            setting    = setting,
            count      = count,
        )
        print(f'   Room Step 2: Naming {count} rooms for {world_name} ({setting})...')

        raw2 = ''
        try:
            raw2 = self.chain.generate_raw(prompt2) or ''
        except Exception as e:
            if DEBUG:
                print(f'   Room Step 2 error: {e}')

        if DEBUG:
            print(f'   Room Step 2 raw: {raw2!r}')

        names = _clean_room_names(raw2, count) if raw2 else []

        if len(names) < max(3, count // 2):
            print(f'   Room Step 2: Only got {len(names)} names — using fallback')
            self._last_method = 'partial_fallback'
            return _apply_fallback(fallback_names, count)

        # Pad if short (shouldn't happen but be safe)
        if len(names) < count:
            extra = ['Side Room', 'Back Room', 'Storage', 'Hallway', 'Utility Room']
            while len(names) < count:
                names.append(extra[len(names) % len(extra)])

        self._last_method = 'llm'
        print(f'   Room Step 2: Got {len(names)} names -> '
              f'{", ".join(names[:4])}{"..." if len(names) > 4 else ""}')
        return names[:count]


def _apply_fallback(fallback: Optional[List[str]], count: int) -> List[str]:
    """Return fallback names padded/trimmed to count."""
    if fallback and len(fallback) >= count:
        return list(fallback[:count])
    generic = ['Entrance', 'Main Room', 'Side Room', 'Back Room',
               'Upper Level', 'Lower Level', 'Hallway', 'Storage',
               'Office', 'Common Area']
    base = list(fallback or []) + generic
    return base[:count]
