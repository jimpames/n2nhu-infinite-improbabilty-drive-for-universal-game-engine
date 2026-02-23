"""
N2NHU World Generator - Sprite Factory
========================================
Generates Sprite objects from plain names + theme context.

The factory is a pure transformation:
    (name, theme_defaults, world_rooms) -> Sprite

Role inference is a keyword classification table — pure data.
Stats are linear functions of theme scalars — pure algebra.
Spawn room assignment is deterministic distribution — pure math.

N2NHU Labs for Applied Artificial Intelligence
"""

import random
from typing import List, Dict, Optional, Tuple
from world_model import Sprite, SpriteRole, WorldConfig
from theme_engine import ThemeDefaults


# Role Classification Table — pure data
ROLE_KEYWORDS: List[Tuple[SpriteRole, List[str]]] = [
    (SpriteRole.VILLAIN, [
        'villain', 'enemy', 'guard', 'soldier', 'officer', 'agent',
        'monster', 'demon', 'dragon', 'dark', 'evil', 'bad', 'boss',
        'commander', 'general', 'overlord', 'antagonist', 'gestapo',
        'mib', 'alien', 'troll', 'orc', 'zombie', 'vampire',
    ]),
    (SpriteRole.BOSS, [
        'boss', 'chief', 'leader', 'king', 'queen', 'emperor',
        'overlord', 'master', 'commander', 'colonel', 'general',
        'admiral', 'director', 'president',
    ]),
    (SpriteRole.ALLY, [
        'ally', 'friend', 'partner', 'companion', 'hero', 'helper',
        'medic', 'doctor', 'nurse', 'priest', 'father', 'chaplain',
        'hawkeye', 'bj', 'radar', 'mulcahy', 'hogan', 'newkirk',
        'carter', 'lebeau', 'kinchloe',
    ]),
    (SpriteRole.NEUTRAL, [
        'clerk', 'shopkeeper', 'merchant', 'civilian', 'villager',
        'butler', 'maid', 'servant', 'cook', 'farmer', 'child',
        'schultz', 'klink', 'igor', 'klinger', 'winchester',
        'margaret', 'potter', 'frank',
    ]),
    (SpriteRole.GUARD, [
        'guard', 'sentry', 'patrol', 'watchman', 'security',
        'trooper', 'private', 'grunt',
    ]),
]

ROLE_BEHAVIOR: Dict[SpriteRole, str] = {
    SpriteRole.HERO:    'ally_support',
    SpriteRole.VILLAIN: 'aggressive_patrol',
    SpriteRole.NEUTRAL: 'neutral_npc',
    SpriteRole.BOSS:    'aggressive_patrol',
    SpriteRole.ALLY:    'ally_support',
    SpriteRole.GUARD:   'patrol_basic',
}

# Known character overrides — specific names get hand-tuned stats
KNOWN_CHARACTER_OVERRIDES: Dict[str, Dict] = {
    'schultz':    {'aggression': 0.05, 'ai_behavior': 'willful_blindness',  'role': SpriteRole.NEUTRAL},
    'klink':      {'aggression': 0.10, 'ai_behavior': 'pompous_bluster',    'role': SpriteRole.NEUTRAL},
    'burkhalter': {'aggression': 0.30, 'ai_behavior': 'pompous_authority',  'role': SpriteRole.NEUTRAL},
    'radar':      {'aggression': 0.05, 'ai_behavior': 'logistics_genius',   'role': SpriteRole.ALLY},
    'klinger':    {'aggression': 0.10, 'ai_behavior': 'escape_artist',      'role': SpriteRole.NEUTRAL},
    'hawkeye':    {'aggression': 0.10, 'ai_behavior': 'ally_wit',           'role': SpriteRole.ALLY},
    'potter':     {'aggression': 0.15, 'ai_behavior': 'commanding_fair',    'role': SpriteRole.ALLY},
    'margaret':   {'aggression': 0.40, 'ai_behavior': 'regulation_authority','role': SpriteRole.NEUTRAL},
    'frank':      {'aggression': 0.65, 'ai_behavior': 'regulation_enforcer','role': SpriteRole.VILLAIN},
    'winchester': {'aggression': 0.20, 'ai_behavior': 'pompous_bluster',    'role': SpriteRole.NEUTRAL},
    'mulcahy':    {'aggression': 0.05, 'ai_behavior': 'moral_compass',      'role': SpriteRole.ALLY},
    'barbie':     {'aggression': 0.02, 'ai_behavior': 'neutral_npc',        'role': SpriteRole.NEUTRAL},
    'ken':        {'aggression': 0.02, 'ai_behavior': 'neutral_npc',        'role': SpriteRole.NEUTRAL},
    'skipper':    {'aggression': 0.01, 'ai_behavior': 'neutral_npc',        'role': SpriteRole.NEUTRAL},
    'tabitha':    {'aggression': 0.05, 'ai_behavior': 'magic_user',         'role': SpriteRole.ALLY},
    'samantha':   {'aggression': 0.05, 'ai_behavior': 'magic_user',         'role': SpriteRole.ALLY},
    'darrin':     {'aggression': 0.10, 'ai_behavior': 'neutral_npc',        'role': SpriteRole.NEUTRAL},
}


class SpriteFactory:
    """
    Generates Sprite objects from character names + theme context.
    Role, stats, and behavior are inferred from name + theme — pure algebra.
    Spawn rooms are distributed deterministically across the world map.
    Every sprite is guaranteed to have valid spawn_rooms.
    """

    def generate_sprites(self, names: List[str], theme: ThemeDefaults,
                         world: WorldConfig) -> Dict[str, Sprite]:
        if not names or not world.rooms:
            return {}

        room_ids = list(world.rooms.keys())
        sprites: Dict[str, Sprite] = {}

        for i, name in enumerate(names):
            if not name.strip():
                continue
            sprite_id = self._make_id(name)
            if sprite_id in sprites:
                sprite_id = f"{sprite_id}_{i}"

            role, behavior, aggression = self._classify(name, theme)
            health, damage = self._calc_stats(role, theme)
            spawn_rooms    = self._assign_spawn_rooms(i, len(names), room_ids)
            loot           = self._assign_loot(world, role)
            description    = self._generate_description(name, role, theme)

            sprites[sprite_id] = Sprite(
                sprite_id    = sprite_id,
                name         = f"{name} (template)",
                description  = description,
                health       = health,
                damage       = damage,
                aggression   = aggression,
                ai_behavior  = behavior,
                spawn_rooms  = spawn_rooms,
                spawn_chance = 0.04 if role in (SpriteRole.ALLY, SpriteRole.NEUTRAL) else 0.06,
                loot_on_death = loot,
                can_pickup   = role != SpriteRole.BOSS,
                role         = role,
            )

        return sprites

    def _make_id(self, name: str) -> str:
        return (name.lower().strip()
                .replace(' ', '_').replace("'", '').replace('-', '_')
                + '_template')

    def _classify(self, name: str, theme: ThemeDefaults) -> Tuple[SpriteRole, str, float]:
        name_lower = name.lower().strip()
        for known, overrides in KNOWN_CHARACTER_OVERRIDES.items():
            if known in name_lower:
                return overrides['role'], overrides['ai_behavior'], overrides['aggression']

        scores: Dict[SpriteRole, int] = {r: 0 for r in SpriteRole}
        for role, keywords in ROLE_KEYWORDS:
            for kw in keywords:
                if kw in name_lower:
                    scores[role] += 1

        best = max(scores, key=lambda r: scores[r])
        if scores[best] == 0:
            best = SpriteRole.NEUTRAL

        behavior   = ROLE_BEHAVIOR.get(best, 'neutral_npc')
        aggression = self._role_aggression(best, theme)
        return best, behavior, aggression

    def _role_aggression(self, role: SpriteRole, theme: ThemeDefaults) -> float:
        lo, hi = theme.sprite_aggression_low, theme.sprite_aggression_high
        mapping = {
            SpriteRole.HERO:    lo,
            SpriteRole.ALLY:    lo,
            SpriteRole.NEUTRAL: lo * 1.5,
            SpriteRole.GUARD:   (lo + hi) / 2,
            SpriteRole.VILLAIN: hi,
            SpriteRole.BOSS:    min(0.95, hi * 1.1),
        }
        return round(mapping.get(role, lo), 2)

    def _calc_stats(self, role: SpriteRole, theme: ThemeDefaults) -> Tuple[int, int]:
        if role == SpriteRole.BOSS:
            return theme.boss_health, int(theme.base_damage * 1.5)
        elif role in (SpriteRole.ALLY, SpriteRole.HERO):
            return int(theme.minion_health * 1.3), int(theme.base_damage * 0.8)
        elif role == SpriteRole.NEUTRAL:
            return int(theme.minion_health * 0.9), int(theme.base_damage * 0.4)
        elif role == SpriteRole.GUARD:
            return theme.minion_health, int(theme.base_damage * 1.1)
        else:
            return int(theme.minion_health * 1.1), theme.base_damage

    def _assign_spawn_rooms(self, idx: int, total: int, room_ids: List[str]) -> List[str]:
        if not room_ids:
            return []
        rooms_per = max(1, len(room_ids) // max(1, total))
        start = (idx * rooms_per) % len(room_ids)
        spawn = []
        for j in range(min(2, rooms_per)):
            spawn.append(room_ids[(start + j) % len(room_ids)])
        return list(dict.fromkeys(spawn))

    def _assign_loot(self, world: WorldConfig, role: SpriteRole) -> str:
        if not world.objects:
            return ''
        candidates = [oid for oid, o in world.objects.items()
                      if o.takeable and o.location != 'none']
        if not candidates:
            return ''
        if role == SpriteRole.BOSS:
            best = [oid for oid in candidates
                    if world.objects[oid].is_weapon or world.objects[oid].is_consumable]
            if best:
                return random.choice(best)
        return random.choice(candidates)

    def _generate_description(self, name: str, role: SpriteRole,
                               theme: ThemeDefaults) -> str:
        desc = {
            SpriteRole.HERO:    f"A central figure in this {theme.flavor_adjective} world.",
            SpriteRole.VILLAIN: f"A hostile presence in this {theme.flavor_noun}.",
            SpriteRole.NEUTRAL: f"A resident of this {theme.flavor_adjective} {theme.flavor_noun}.",
            SpriteRole.BOSS:    f"The most dangerous entity in this {theme.flavor_noun}.",
            SpriteRole.ALLY:    f"A trustworthy ally in this {theme.flavor_adjective} world.",
            SpriteRole.GUARD:   f"A patrol element in this {theme.flavor_adjective} {theme.flavor_noun}.",
        }
        return f"{name}. {desc.get(role, 'A character in this world.')}"
