"""
world_interview.py — N2NHU World Knowledge Interview
=====================================================
Jim's architectural insight: every downstream step (room namer, sprite
namer, object enricher, SD suffix) was doing its own isolated LLM
discovery. When any one step got the world wrong, everything it produced
was poisoned.

The fix: ONE interview before everything else. Multi-turn dialogue that
establishes validated ground truth about the world, then feeds that
context to ALL downstream steps as a single source of truth.

Interview flow:
  Turn 1 — Open description: "Tell me about ADAM 12 in 2-3 sentences"
  Turn 2 — Structured extraction: parse genre, setting, era, characters
  Turn 3 — Cross-validate: "You said LAPD patrol show with Malloy/Reed — Yes or No?"
  Turn 4 — Correct if No, re-confirm if corrected

WorldContext is then consumed by:
  - LLMThemeClassifier   (genre)
  - LLMRoomNamer         (setting + location)
  - WorldContentEnricher (characters + object_categories)
  - get_setting_suffix   (setting → SD visual override)

N2NHU Labs for Applied Artificial Intelligence
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ── WorldContext — the shared ground truth ───────────────────

@dataclass
class WorldContext:
    """
    Validated knowledge about a world, established by interview.
    All downstream steps consume this instead of doing their own discovery.
    """
    world_name:        str
    description:       str         = ''   # "1968 LAPD police procedural TV show"
    genre:             str         = ''   # "CRIME_SPY", "SITCOM", "SCIFI"...
    setting:           str         = ''   # "LAPD PATROL CAR AND PRECINCT"
    location:          str         = ''   # "LOS ANGELES 1970s"
    time_period:       str         = ''   # "1960s", "1970s", "2350s"...
    characters:        List[str]   = field(default_factory=list)
    object_categories: List[str]   = field(default_factory=list)
    confidence:        str         = 'low'  # 'high' / 'medium' / 'low'
    method:            str         = 'fallback'

    def is_valid(self) -> bool:
        """True if we have enough to anchor downstream steps."""
        return bool(self.setting and self.characters)

    def anchor_summary(self) -> str:
        """One-line summary used as context in downstream prompts."""
        chars = ', '.join(self.characters[:4])
        return (f"{self.world_name} ({self.description or self.genre}) — "
                f"set in {self.setting or 'unknown'}"
                + (f", {self.location}" if self.location else '')
                + (f". Main characters: {chars}" if chars else ''))


# ── Interview Prompts ─────────────────────────────────────────

DESCRIBE_PROMPT = """\
In 2-3 sentences, describe: {world_name}

What kind of show/game/story is it? When was it set? \
Where does the main action take place?

Be specific. If you don't recognise it, say so."""


EXTRACT_PROMPT = """\
Based on this description of {world_name}:
"{description}"

Extract these facts. Return ONLY this exact format, one item per line:
GENRE: (one of: SITCOM, CRIME_SPY, SCIFI, FANTASY, HORROR, ADVENTURE, MILITARY, WESTERN, OTHER)
SETTING: (1-4 words, physical location e.g. LAPD PRECINCT, TROPICAL ISLAND, SPACE STATION)
LOCATION: (city/region/planet e.g. LOS ANGELES, SOUTH PACIFIC, DEEP SPACE)
ERA: (decade e.g. 1970s, 1960s, 2350s, PREHISTORIC)
CHARACTERS: (comma-separated real character names, first 5 only)
OBJECTS: (comma-separated prop/object types you would find there, first 6 only)"""


VALIDATE_PROMPT = """\
For {world_name}, I extracted these facts:
  Setting:    {setting}
  Location:   {location}
  Characters: {characters}
  Genre:      {genre}

Are ALL of these facts correct for {world_name}?

You MUST answer with ONLY the single word "Yes" or "No".
Do not explain. Do not qualify. One word only: Yes or No."""


CORRECT_PROMPT = """\
Some of these facts about {world_name} are wrong:
  Setting:    {setting}
  Location:   {location}
  Characters: {characters}
  Genre:      {genre}

Return ONLY the corrected version in this exact format:
GENRE: ...
SETTING: ...
LOCATION: ...
ERA: ...
CHARACTERS: ...
OBJECTS: ..."""


UNKNOWN_FALLBACK_PROMPT = """\
I don't recognise "{world_name}" as a specific show or game.
Please describe what you DO know or can infer from the name.

Return ONLY:
GENRE: (best guess)
SETTING: (best guess 1-4 words)
LOCATION: (best guess)
ERA: (best guess)
CHARACTERS: (generic character types if unknown)
OBJECTS: (generic objects that might appear)"""


MAX_ROUNDS = 2   # confirm → correct → re-confirm maximum


# ── Response Parsers ──────────────────────────────────────────

def _extract_field(text: str, field: str) -> str:
    """Extract 'FIELD: value' from LLM structured output."""
    m = re.search(rf'^{field}:\s*(.+)$', text, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else ''


def _parse_csv(text: str) -> List[str]:
    """Parse comma-separated values, cleaning noise."""
    items = [i.strip().strip('"\'') for i in text.split(',')]
    return [i for i in items if i and len(i) > 1]


def _parse_structured(text: str) -> dict:
    """Parse a structured FIELD: value response into a dict."""
    return {
        'genre':      _extract_field(text, 'GENRE'),
        'setting':    _extract_field(text, 'SETTING'),
        'location':   _extract_field(text, 'LOCATION'),
        'era':        _extract_field(text, 'ERA'),
        'characters': _parse_csv(_extract_field(text, 'CHARACTERS')),
        'objects':    _parse_csv(_extract_field(text, 'OBJECTS')),
    }


def _is_yes(text: str) -> bool:
    """Extract Yes/No from potentially verbose LLM response. Take first real word."""
    # Strip leading non-alpha, then strip everything after first punctuation
    cleaned = re.sub(r'^[^a-zA-Z]*', '', text.strip())
    first_word = cleaned.strip().lower().split()[0].rstrip('.,!') if cleaned.strip() else ''
    return first_word in ('yes', 'y', 'yep', 'yup', 'correct', 'right',
                          'true', 'affirmative', 'absolutely', 'indeed',
                          'confirmed', 'accurate', 'all')


def _is_no(text: str) -> bool:
    """Extract No from potentially verbose LLM response."""
    cleaned = re.sub(r'^[^a-zA-Z]*', '', text.strip())
    first_word = cleaned.strip().lower().split()[0].rstrip('.,!') if cleaned.strip() else ''
    return first_word in ('no', 'n', 'nope', 'incorrect', 'wrong',
                          'false', 'negative', 'not')


def _is_unknown(description: str) -> bool:
    """Check if Llama admitted it doesn't recognise the world."""
    markers = ["don't recognise", "don't know", "not familiar",
               "no information", "cannot find", "unclear", "unknown"]
    d = description.lower()
    return any(m in d for m in markers)


# ── Main Interview Class ──────────────────────────────────────

class WorldKnowledgeInterview:
    """
    Multi-turn LLM interview that establishes validated WorldContext
    before any world generation begins.

    Usage:
        interview = WorldKnowledgeInterview(provider_chain)
        ctx = interview.run("ADAM 12")
        # ctx.setting == "LAPD PATROL CAR"
        # ctx.characters == ["Pete Malloy", "Jim Reed", "Sgt. MacDonald"]
        # ctx.object_categories == ["patrol car", "police radio", "badge"]
    """

    def __init__(self, provider_chain):
        self.chain = provider_chain

    def _ask(self, prompt: str) -> str:
        """Ask a single question, return empty string on failure."""
        try:
            return self.chain.generate_raw(prompt) or ''
        except Exception:
            return ''

    def run(self, world_name: str) -> WorldContext:
        """
        Run the full interview. Returns validated WorldContext.
        Falls back gracefully if LLM unavailable.
        """
        ctx = WorldContext(world_name=world_name)

        # ── Turn 1: Open description ──────────────────────────
        print(f'   Interview T1: Describe {world_name!r}...')
        raw_desc = self._ask(DESCRIBE_PROMPT.format(world_name=world_name))

        if not raw_desc:
            print(f'   Interview: LLM unavailable — using fallback context')
            ctx.method = 'fallback'
            return ctx

        description = raw_desc.strip()
        ctx.description = description[:200]
        print(f'   Interview T1: {description[:80]}...')

        # ── Turn 2: Structured extraction ─────────────────────
        # If Llama admitted it doesn't know, use fallback extraction
        if _is_unknown(description):
            print(f'   Interview T2: World unknown — using name-based inference')
            raw_struct = self._ask(
                UNKNOWN_FALLBACK_PROMPT.format(world_name=world_name))
        else:
            print(f'   Interview T2: Extracting structured facts...')
            raw_struct = self._ask(
                EXTRACT_PROMPT.format(
                    world_name  = world_name,
                    description = description,
                ))

        if not raw_struct:
            print(f'   Interview: No structured response — using description only')
            ctx.method = 'description_only'
            return ctx

        facts = _parse_structured(raw_struct)
        print(f'   Interview T2: genre={facts["genre"]!r} '
              f'setting={facts["setting"]!r} '
              f'chars={facts["characters"][:3]}')

        # ── Turn 3: Cross-validate ─────────────────────────────
        if facts['setting'] and facts['characters']:
            chars_str = ', '.join(facts['characters'][:5])
            print(f'   Interview T3: Validating facts...')
            raw_validate = self._ask(
                VALIDATE_PROMPT.format(
                    world_name = world_name,
                    setting    = facts['setting'],
                    location   = facts['location'],
                    characters = chars_str,
                    genre      = facts['genre'],
                ))

            if raw_validate and _is_no(raw_validate):
                # ── Turn 4: Correct ───────────────────────────
                print(f'   Interview T3: LLM flagged errors — requesting correction...')
                raw_correct = self._ask(
                    CORRECT_PROMPT.format(
                        world_name = world_name,
                        setting    = facts['setting'],
                        location   = facts['location'],
                        characters = chars_str,
                        genre      = facts['genre'],
                    ))
                if raw_correct:
                    corrected = _parse_structured(raw_correct)
                    # Merge corrections — only override non-empty fields
                    for key in ('genre', 'setting', 'location',
                                'era', 'characters', 'objects'):
                        val = corrected.get(key)
                        if val:
                            facts[key] = val
                    print(f'   Interview T4: Corrected -> '
                          f'setting={facts["setting"]!r} '
                          f'chars={facts["characters"][:3]}')

                    # Re-validate after correction
                    chars_str2 = ', '.join(facts['characters'][:5])
                    raw_recheck = self._ask(
                        VALIDATE_PROMPT.format(
                            world_name = world_name,
                            setting    = facts['setting'],
                            location   = facts['location'],
                            characters = chars_str2,
                            genre      = facts['genre'],
                        ))
                    if raw_recheck and _is_yes(raw_recheck):
                        print(f'   Interview T4: Re-validated ✅')
                        ctx.confidence = 'high'
                    else:
                        print(f'   Interview T4: Still uncertain — using best guess')
                        ctx.confidence = 'medium'
                else:
                    ctx.confidence = 'medium'

            elif raw_validate and _is_yes(raw_validate):
                print(f'   Interview T3: Validated ✅')
                ctx.confidence = 'high'
            else:
                print(f'   Interview T3: Ambiguous — proceeding with caution')
                ctx.confidence = 'medium'
        else:
            ctx.confidence = 'low'

        # ── Populate context from validated facts ──────────────
        ctx.genre             = facts.get('genre', '').upper()
        ctx.setting           = facts.get('setting', '').upper()
        ctx.location          = facts.get('location', '').upper()
        ctx.time_period       = facts.get('era', '')
        ctx.characters        = facts.get('characters', [])
        ctx.object_categories = facts.get('objects', [])
        ctx.method            = 'llm_interview'

        return ctx
