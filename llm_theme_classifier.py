"""
N2NHU Infinite Improbability Drive - LLM Theme Classifier
==========================================================
Two-step LLM-based theme detection for world names that
keyword matching can't handle.

THE PROBLEM:
  The keyword classifier in theme_engine.py scores against
  a table of known words. It works perfectly for:
    "MASH 4077"   -> MILITARY  (keyword: 'mash')
    "Bewitched"   -> SITCOM    (keyword: 'bewitched')
  But fails on:
    "STUDIO 54 DISCO NYC" -> ORIGINAL  (no keyword match)
    "Three's Company"     -> ORIGINAL  (no keyword match)
    "The Wire"            -> ORIGINAL  (no keyword match)

THE FIX - Two-Step Classification:
  Step 1: Ask Llama what genre/setting [world_name] is.
    "What single word describes Three's Company?
     Examples: Studio 54 = DISCO, MASH 4077th = MILITARY"
    -> Llama: "SITCOM"

  Step 2: Map that word to our WorldTheme enum.
    SITCOM -> WorldTheme.SITCOM
    DISCO  -> WorldTheme.DISCO
    etc.

  Fallback: If LLM unavailable or returns unrecognizable
  category, falls back to keyword matching as before.

Usage in create_world.py:
  from llm_theme_classifier import LLMThemeClassifier
  classifier = LLMThemeClassifier(provider_chain)
  theme = classifier.classify(world_name)
  defaults = engine.get_defaults_for_theme(theme)

N2NHU Labs for Applied Artificial Intelligence
"""

import re
import os
from typing import Optional
from world_model import WorldTheme


# ── Debug ─────────────────────────────────────────────────────
DEBUG = os.environ.get('N2NHU_DEBUG', '0') == '1'


# ── Step 1 Prompt: Discovery ──────────────────────────────────

THEME_DISCOVERY_PROMPT = """\
If MASH 4077th is a MILITARY show and THREE'S COMPANY is a SITCOM \
and STUDIO 54 is a DISCO then what is the most probable single-word \
descriptor for: {world_name}

More examples to calibrate your answer:
- Bewitched            -> SITCOM
- Hogans Heroes        -> MILITARY
- Area 51              -> SCIFI
- Barbie World         -> DOMESTIC
- Dracula's Castle     -> HORROR
- Indiana Jones        -> ADVENTURE
- James Bond           -> SPY
- Cheers               -> SITCOM
- The Flintstones      -> DOMESTIC
- Star Trek            -> SCIFI
- Haunted Mansion      -> HORROR
- Chuck E. Cheese's    -> DOMESTIC
- Saturday Night Fever -> DISCO
- The Wire             -> CRIME
- Miami Vice           -> CRIME
- Fantasy Island       -> ADVENTURE
- The Love Boat        -> SITCOM
- Gilligan's Island    -> ADVENTURE
- Sesame Street        -> DOMESTIC
- Mister Rogers        -> DOMESTIC
- Disney World         -> ADVENTURE

Return ONLY one word. No explanation. No punctuation."""


# ── Step 2 Prompt: Confirmation ───────────────────────────────

THEME_CONFIRM_PROMPT = """\
You said the genre/setting of "{world_name}" is "{llm_theme}".

Now choose the single best match from this exact list:
SCIFI, MILITARY, FANTASY, DOMESTIC, HORROR, ADVENTURE, SITCOM, DISCO, NIGHTCLUB, CRIME_SPY

Rules:
- If it's a nightclub, disco, dance club, or rave -> DISCO or NIGHTCLUB
- If it's a TV sitcom, comedy show, or apartment comedy -> SITCOM
- If it's a war, army, or military setting -> MILITARY
- If it's science fiction, space, or alien -> SCIFI
- If it's magical, wizards, or medieval -> FANTASY
- If it's horror, haunted, or supernatural -> HORROR
- If it's crime, spy, detective, or thriller -> CRIME_SPY
- If it's home, family, or domestic -> DOMESTIC
- If it's exploration, jungle, or adventure -> ADVENTURE

Return ONLY one word from the list above."""


# ── Keyword Challenge Prompt ──────────────────────────────────
# Jim's design: when keyword matching fires, challenge it with the LLM.
# "If BARNEY MILLER isn't a NIGHTCLUB then what is a more
#  accurate theme setting description?"
# This catches false positives like 'bar' in 'barney' -> NIGHTCLUB.

KEYWORD_CHALLENGE_PROMPT = """\
If {world_name} is NOT actually a {kw_theme} setting, \
what is a more accurate single-word theme descriptor?

Known examples to calibrate your answer:
- MASH 4077th           -> MILITARY  (not a nightclub)
- THREE'S COMPANY       -> SITCOM    (not a nightclub)
- STUDIO 54             -> DISCO     (correct)
- BARNEY MILLER         -> CRIME_SPY (police precinct sitcom, NOT a nightclub)
- CHEERS                -> SITCOM    (bar setting but it's a sitcom)
- MIAMI VICE            -> CRIME_SPY (not domestic)
- BEWITCHED             -> SITCOM    (not fantasy)

Choose from: SCIFI, MILITARY, FANTASY, DOMESTIC, HORROR, ADVENTURE, SITCOM, DISCO, NIGHTCLUB, CRIME_SPY

If {kw_theme} IS actually correct for {world_name}, return {kw_theme} unchanged.
Return ONLY one word. No explanation."""


# ── LLM word -> WorldTheme mapping ───────────────────────────

# Maps what the LLM might say -> WorldTheme enum value
# Covers synonyms, partial matches, common Llama responses
THEME_WORD_MAP = {
    # SCIFI
    'scifi':        WorldTheme.SCIFI,
    'sci-fi':       WorldTheme.SCIFI,
    'science':      WorldTheme.SCIFI,
    'fiction':      WorldTheme.SCIFI,
    'space':        WorldTheme.SCIFI,
    'alien':        WorldTheme.SCIFI,
    'futuristic':   WorldTheme.SCIFI,
    'tech':         WorldTheme.SCIFI,

    # MILITARY
    'military':     WorldTheme.MILITARY,
    'war':          WorldTheme.MILITARY,
    'army':         WorldTheme.MILITARY,
    'combat':       WorldTheme.MILITARY,
    'soldier':      WorldTheme.MILITARY,
    'wartime':      WorldTheme.MILITARY,
    'battlefield':  WorldTheme.MILITARY,

    # FANTASY
    'fantasy':      WorldTheme.FANTASY,
    'magic':        WorldTheme.FANTASY,
    'medieval':     WorldTheme.FANTASY,
    'wizard':       WorldTheme.FANTASY,
    'magical':      WorldTheme.FANTASY,
    'fairy':        WorldTheme.FANTASY,
    'mythical':     WorldTheme.FANTASY,

    # DOMESTIC (includes kids venues, family places, home settings)
    'domestic':     WorldTheme.DOMESTIC,
    'home':         WorldTheme.DOMESTIC,
    'family':       WorldTheme.DOMESTIC,
    'suburban':     WorldTheme.DOMESTIC,
    'household':    WorldTheme.DOMESTIC,
    'kids':         WorldTheme.DOMESTIC,
    'children':     WorldTheme.DOMESTIC,
    'pizza':        WorldTheme.DOMESTIC,
    'arcade':       WorldTheme.DOMESTIC,
    'party':        WorldTheme.DOMESTIC,
    'playground':   WorldTheme.DOMESTIC,
    'restaurant':   WorldTheme.DOMESTIC,
    'entertainment':WorldTheme.DOMESTIC,

    # HORROR
    'horror':       WorldTheme.HORROR,
    'scary':        WorldTheme.HORROR,
    'haunted':      WorldTheme.HORROR,
    'gothic':       WorldTheme.HORROR,
    'supernatural': WorldTheme.HORROR,
    'dark':         WorldTheme.HORROR,
    'vampire':      WorldTheme.HORROR,
    'zombie':       WorldTheme.HORROR,

    # ADVENTURE
    'adventure':    WorldTheme.ADVENTURE,
    'exploration':  WorldTheme.ADVENTURE,
    'jungle':       WorldTheme.ADVENTURE,
    'explorer':     WorldTheme.ADVENTURE,
    'treasure':     WorldTheme.ADVENTURE,

    # SITCOM
    'sitcom':       WorldTheme.SITCOM,
    'comedy':       WorldTheme.SITCOM,
    'sitcoms':      WorldTheme.SITCOM,
    'television':   WorldTheme.SITCOM,
    'tv':           WorldTheme.SITCOM,
    'apartment':    WorldTheme.SITCOM,
    'neighbors':    WorldTheme.SITCOM,
    'neighbors':    WorldTheme.SITCOM,
    'romantic':     WorldTheme.SITCOM,

    # DISCO / NIGHTCLUB
    'disco':        WorldTheme.DISCO,
    'dance':        WorldTheme.DISCO,
    'club':         WorldTheme.DISCO,
    'discotheque':  WorldTheme.DISCO,
    'dj':           WorldTheme.DISCO,
    'nightlife':    WorldTheme.DISCO,
    'nightclub':    WorldTheme.NIGHTCLUB,
    'bar':          WorldTheme.NIGHTCLUB,
    'lounge':       WorldTheme.NIGHTCLUB,
    'cabaret':      WorldTheme.NIGHTCLUB,

    # CRIME_SPY
    'crime':        WorldTheme.CRIME_SPY,
    'spy':          WorldTheme.CRIME_SPY,
    'crime_spy':    WorldTheme.CRIME_SPY,
    'thriller':     WorldTheme.CRIME_SPY,
    'detective':    WorldTheme.CRIME_SPY,
    'noir':         WorldTheme.CRIME_SPY,
    'heist':        WorldTheme.CRIME_SPY,
    'gangster':     WorldTheme.CRIME_SPY,
    'criminal':     WorldTheme.CRIME_SPY,
    'espionage':    WorldTheme.CRIME_SPY,
}


def _extract_theme_word(text: str) -> Optional[str]:
    """Pull the single theme word out of an LLM response."""
    text = text.strip()

    # Remove preamble like "The genre is DISCO" or "I would say MILITARY"
    text = re.sub(r'^(the\s+)?(genre|setting|theme|category|world)\s+(is|would be|of|for)[:\s]+',
                  '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(i would say|i think|it is|that would be)[:\s]+',
                  '', text, flags=re.IGNORECASE)

    # Get the first word that looks like a theme word (all caps preferred)
    # Try all-caps word first
    m = re.search(r'\b([A-Z_]{3,})\b', text)
    if m:
        return m.group(1).upper()

    # Fall back to first substantial word
    words = text.strip().split()
    if words:
        return words[0].upper().strip('.,!?"\':')

    return None


def _map_to_theme(word: str) -> Optional[WorldTheme]:
    """Map a raw LLM word to a WorldTheme enum value."""
    if not word:
        return None
    key = word.lower().strip('.,!?"\':').replace('-', '_').replace(' ', '_')

    # Direct lookup
    if key in THEME_WORD_MAP:
        return THEME_WORD_MAP[key]

    # Partial match — word starts with a known key
    for map_key, theme in THEME_WORD_MAP.items():
        if key.startswith(map_key) or map_key.startswith(key):
            return theme

    return None


class LLMThemeClassifier:
    """
    Two-step LLM theme classifier.
    Falls back to keyword classifier if LLM unavailable.
    """

    def __init__(self, provider_chain, keyword_classifier=None):
        self.chain = provider_chain
        self.keyword_classifier = keyword_classifier  # ThemeEngine.classify fallback
        self._last_llm_word = None    # for logging
        self._last_method = None      # 'llm' or 'keyword'

    @property
    def last_llm_word(self):
        return self._last_llm_word

    @property
    def last_method(self):
        return self._last_method

    def classify(self, world_name: str) -> WorldTheme:
        """
        Classify world_name into a WorldTheme using two-step LLM prompting.
        Falls back to keyword matching if LLM fails.
        """
        # Try keyword classifier first for known worlds (fast path)
        # BUT: challenge the result with the LLM to catch false positives
        # e.g. 'bar' in 'BARNEY' fires NIGHTCLUB — LLM corrects it to CRIME_SPY
        if self.keyword_classifier:
            kw_result = self.keyword_classifier(world_name)
            if kw_result != WorldTheme.ORIGINAL:
                # Challenge the keyword hit with LLM
                kw_name = kw_result.value.upper().replace('_', ' ')
                prompt_challenge = KEYWORD_CHALLENGE_PROMPT.format(
                    world_name = world_name,
                    kw_theme   = kw_name,
                )
                print(f'   Theme: keyword hit {kw_name!r} — challenging with LLM...')
                raw_challenge = ''
                try:
                    raw_challenge = self.chain.generate_raw(prompt_challenge) or ''
                except Exception:
                    pass

                if raw_challenge:
                    challenged_word = _extract_theme_word(raw_challenge)
                    challenged_theme = _map_to_theme(challenged_word) if challenged_word else None
                    if challenged_theme and challenged_theme != kw_result:
                        print(f'   Theme: LLM overrode keyword: '
                              f'{kw_result.value} -> {challenged_theme.value}')
                        self._last_method   = 'keyword_challenged'
                        self._last_llm_word = challenged_word
                        return challenged_theme
                    else:
                        # LLM confirmed the keyword result
                        print(f'   Theme: LLM confirmed keyword: {kw_result.value}')
                        self._last_method   = 'keyword_confirmed'
                        self._last_llm_word = challenged_word
                        return kw_result
                else:
                    # LLM unavailable — trust the keyword result
                    self._last_method   = 'keyword'
                    self._last_llm_word = None
                    if DEBUG:
                        print(f'  Theme: keyword match -> {kw_result.value}')
                    return kw_result

        # Step 1: Ask Llama what genre/setting this is
        prompt1 = THEME_DISCOVERY_PROMPT.format(world_name=world_name)
        if DEBUG:
            print(f'  Theme Step 1: classifying {world_name!r}...')

        raw1 = ''
        try:
            raw1 = self.chain.generate_raw(prompt1) or ''
        except Exception as e:
            if DEBUG:
                print(f'  Theme Step 1 error: {e}')

        if DEBUG:
            print(f'  Theme Step 1 raw: {raw1!r}')

        word1 = _extract_theme_word(raw1)
        theme = _map_to_theme(word1) if word1 else None

        if theme:
            self._last_llm_word = word1
            self._last_method = 'llm_step1'
            print(f'   Theme: {world_name} -> {word1} -> {theme.value}')
            return theme

        # Step 2: If step 1 mapping failed, ask for explicit category choice
        if word1:
            prompt2 = THEME_CONFIRM_PROMPT.format(
                world_name=world_name, llm_theme=word1)
            if DEBUG:
                print(f'  Theme Step 2: mapping {word1!r}...')
            try:
                raw2 = self.chain.generate_raw(prompt2) or ''
                word2 = _extract_theme_word(raw2)
                theme = _map_to_theme(word2) if word2 else None
                if theme:
                    self._last_llm_word = f'{word1} -> {word2}'
                    self._last_method = 'llm_step2'
                    print(f'   Theme: {world_name} -> {word1} -> {word2} -> {theme.value}')
                    return theme
            except Exception as e:
                if DEBUG:
                    print(f'  Theme Step 2 error: {e}')

        # Final fallback: keyword classifier or ORIGINAL
        if self.keyword_classifier:
            fallback = self.keyword_classifier(world_name)
            self._last_method = 'keyword_fallback'
            self._last_llm_word = word1
            print(f'   Theme: LLM unclear ({word1!r}) -> keyword fallback -> {fallback.value}')
            return fallback

        self._last_method = 'original_fallback'
        self._last_llm_word = word1
        return WorldTheme.ORIGINAL
