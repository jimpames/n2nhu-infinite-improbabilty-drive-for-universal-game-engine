"""
N2NHU World Generator - World Model
====================================
Pure algebraic dataclasses. Every game world is a set of transformation
matrices. This module defines those matrices as typed Python dataclasses.

Philosophy: A world is not a program. It is a configuration of state
transitions. The engine executes the transitions. The generator produces
the configuration. The model enforces the algebra.

N2NHU Labs for Applied Artificial Intelligence
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


# ── Enumerations (the type algebra) ─────────────────────────

class AIBehavior(Enum):
    AGGRESSIVE_PATROL  = "aggressive_patrol"
    PATROL_BASIC       = "patrol_basic"
    WILLFUL_BLINDNESS  = "willful_blindness"
    NEUTRAL_NPC        = "neutral_npc"
    ALLY_SUPPORT       = "ally_support"
    PASSIVE            = "passive"
    INVESTIGATOR       = "investigator"
    LOGISTICS          = "logistics_genius"
    MORAL_COMPASS      = "moral_compass"
    COMMANDING         = "commanding_fair"
    POMPOUS            = "pompous_bluster"
    ESCAPE_ARTIST      = "escape_artist"

class SpriteRole(Enum):
    HERO    = "hero"
    VILLAIN = "villain"
    NEUTRAL = "neutral"
    BOSS    = "boss"
    ALLY    = "ally"
    GUARD   = "guard"

class PhysicsType(Enum):
    TEMPERATURE    = "temperature"
    ENERGY         = "energy"
    LOCK_KEY       = "lock_key"
    CRAFTING       = "crafting"
    TELEPORTATION  = "teleportation"
    DISGUISE       = "disguise"
    EXPLOSIVES     = "explosives"
    BRIBERY        = "bribery"
    MAGIC          = "magic"
    MEDICAL        = "medical"
    GROWTH         = "growth"
    ALIEN_TECH     = "alien_tech"

class WorldTheme(Enum):
    SCIFI       = "scifi"
    MILITARY    = "military"
    FANTASY     = "fantasy"
    DOMESTIC    = "domestic"
    HORROR      = "horror"
    ADVENTURE   = "adventure"
    SITCOM      = "sitcom"
    CRIME_SPY   = "crime_spy"
    DISCO       = "disco"
    NIGHTCLUB   = "nightclub"
    ORIGINAL    = "original"


# ── Room Matrix ──────────────────────────────────────────────

@dataclass
class Room:
    """
    A room is a node in the world graph.
    Exits are directed edges to other nodes.
    Properties are transformation triggers.
    """
    room_id:     str
    name:        str
    description: str
    exits:       Dict[str, str] = field(default_factory=dict)  # direction -> room_id
    properties:  Dict[str, str] = field(default_factory=dict)  # key -> value
    is_start:    bool = False

    def to_ini_section(self) -> Dict[str, str]:
        """Serialize to INI key-value pairs."""
        d = {
            'name':        self.name,
            'description': self.description,
        }
        d.update(self.exits)
        d.update(self.properties)
        if self.is_start:
            d['start'] = 'true'
        return d

    def validate(self, all_room_ids: Set[str]) -> List[str]:
        errors = []
        if not self.name.strip():
            errors.append(f"[{self.room_id}] missing name")
        if not self.description.strip():
            errors.append(f"[{self.room_id}] missing description")
        for direction, target in self.exits.items():
            if target not in all_room_ids:
                errors.append(f"[{self.room_id}] exit '{direction}' -> '{target}' MISSING room")
        return errors


# ── Object Matrix ────────────────────────────────────────────

@dataclass
class GameObject:
    """
    An object is a named entity with a location and a verb permission set.
    Objects are the operands in transformation rules.
    """
    object_id:    str
    name:         str
    description:  str
    location:     str                         # room_id or container object_id
    takeable:     bool = True
    is_weapon:    bool = False
    damage:       int  = 0
    is_consumable: bool = False
    health_restore: int = 0
    is_container: bool = False
    is_wearable:  bool = False
    bribe_value:  str  = ""
    valid_verbs:  List[str] = field(default_factory=list)
    properties:   Dict[str, str] = field(default_factory=dict)

    def to_ini_section(self) -> Dict[str, str]:
        d = {
            'name':        self.name,
            'description': self.description,
            'location':    self.location,
            'takeable':    str(self.takeable).lower(),
        }
        if self.is_weapon:
            d['weapon'] = 'true'
            d['damage'] = str(self.damage)
        if self.is_consumable:
            d['consumable']     = 'true'
            d['health_restore'] = str(self.health_restore)
        if self.is_container:
            d['container'] = 'true'
        if self.is_wearable:
            d['wearable'] = 'true'
            d['worn']     = 'false'
        if self.bribe_value:
            d['bribe_value'] = self.bribe_value
        if self.valid_verbs:
            d['valid_verbs'] = ', '.join(self.valid_verbs)
        d.update(self.properties)
        return d

    def validate(self, all_room_ids: Set[str], all_object_ids: Set[str]) -> List[str]:
        errors = []
        if not self.name.strip():
            errors.append(f"[{self.object_id}] missing name")
        if self.location and self.location != 'none':
            if self.location not in all_room_ids and self.location not in all_object_ids:
                errors.append(f"[{self.object_id}] location='{self.location}' MISSING")
        return errors


# ── Sprite Matrix ────────────────────────────────────────────

@dataclass
class Sprite:
    """
    A sprite is an autonomous agent with behavior parameters.
    Behavior is encoded as enumerated AI strategy plus numeric scalars.
    """
    sprite_id:    str
    name:         str
    description:  str
    health:       int
    damage:       int
    aggression:   float                        # 0.0 → 1.0
    ai_behavior:  str
    spawn_rooms:  List[str] = field(default_factory=list)
    spawn_chance: float = 0.03
    loot_on_death: str = ""
    can_pickup:   bool = False
    role:         SpriteRole = SpriteRole.NEUTRAL
    properties:   Dict[str, str] = field(default_factory=dict)

    def to_ini_section(self) -> Dict[str, str]:
        d = {
            'type':        'sprite',
            'name':        self.name,
            'description': self.description,
            'health':      str(self.health),
            'damage':      str(self.damage),
            'aggression':  str(self.aggression),
            'ai_behavior': self.ai_behavior,
            'spawn_rooms': ', '.join(self.spawn_rooms),
            'spawn_chance': str(self.spawn_chance),
            'can_pickup':  str(self.can_pickup).lower(),
            'takeable':    'false',
        }
        if self.loot_on_death:
            d['loot_on_death'] = self.loot_on_death
        d.update(self.properties)
        return d

    def validate(self, all_room_ids: Set[str], all_object_ids: Set[str]) -> List[str]:
        errors = []
        if not self.name.strip():
            errors.append(f"[{self.sprite_id}] missing name")
        for r in self.spawn_rooms:
            if r not in all_room_ids:
                errors.append(f"[{self.sprite_id}] spawn_room '{r}' MISSING")
        if self.loot_on_death and self.loot_on_death not in all_object_ids:
            errors.append(f"[{self.sprite_id}] loot_on_death '{self.loot_on_death}' MISSING")
        return errors


# ── Transformation Matrix ────────────────────────────────────

@dataclass
class Transformation:
    """
    A transformation is a state transition rule.
    object_id + state + trigger_conditions → new_state + optional_side_effects

    This is the core algebraic unit of the engine.
    Everything that 'happens' in a world is a transformation.
    """
    transform_id:       str
    object_id:          str
    state:              str
    turns_required:     int
    new_state:          str
    message:            str
    new_object_id:      str = ""
    requires_object:    str = ""
    requires_object_2:  str = ""
    location_property:  str = ""
    new_location:       str = ""
    properties:         Dict[str, str] = field(default_factory=dict)

    def to_ini_section(self) -> Dict[str, str]:
        d = {
            'object_id':      self.object_id,
            'state':          self.state,
            'turns_required': str(self.turns_required),
            'new_state':      self.new_state,
            'message':        self.message,
        }
        if self.new_object_id:
            d['new_object_id'] = self.new_object_id
        if self.requires_object:
            d['requires_object'] = self.requires_object
        if self.requires_object_2:
            d['requires_object_2'] = self.requires_object_2
        if self.location_property:
            d['location_has_property'] = self.location_property
        if self.new_location:
            d['new_location'] = self.new_location
        d.update(self.properties)
        return d

    def validate(self, all_object_ids: Set[str], all_room_ids: Set[str]) -> List[str]:
        errors = []
        if self.object_id not in all_object_ids:
            errors.append(f"[{self.transform_id}] object_id='{self.object_id}' MISSING")
        if self.new_object_id and self.new_object_id not in all_object_ids:
            errors.append(f"[{self.transform_id}] new_object_id='{self.new_object_id}' MISSING")
        if self.requires_object and self.requires_object not in all_object_ids:
            errors.append(f"[{self.transform_id}] requires_object='{self.requires_object}' MISSING")
        if self.requires_object_2 and self.requires_object_2 not in all_object_ids:
            errors.append(f"[{self.transform_id}] requires_object_2='{self.requires_object_2}' MISSING")
        if self.new_location and self.new_location not in all_room_ids:
            errors.append(f"[{self.transform_id}] new_location='{self.new_location}' MISSING")
        return errors


# ── Combat Matrix ────────────────────────────────────────────

@dataclass
class CombatConfig:
    """
    Combat parameters define the damage algebra.
    Damage is a linear transformation of base_damage × weapon_multiplier.
    """
    base_damage:      int   = 10
    weapon_multiplier: float = 1.0
    respawn_location: str   = ""
    death_penalty:    int   = 3
    friendly_fire:    bool  = False
    damage_types:     Dict[str, float] = field(default_factory=lambda: {
        'slashing': 1.0, 'piercing': 1.1, 'blunt': 0.9, 'explosive': 2.0
    })

    def to_ini_sections(self, respawn_room: str) -> Dict[str, Dict[str, str]]:
        sections = {
            'player_vs_player': {
                'base_damage':       str(self.base_damage),
                'weapon_multiplier': str(self.weapon_multiplier),
                'can_attack':        'true',
                'requires_pvp_mode': 'true',
                'effect':            'none',
                'message_hit':       'You strike {target} for {damage} damage!',
                'message_kill':      'You have taken down {target}!',
            },
            'player_vs_sprite': {
                'base_damage':       str(self.base_damage),
                'weapon_multiplier': str(self.weapon_multiplier),
                'can_attack':        'true',
                'requires_pvp_mode': 'false',
                'effect':            'loot_drop',
                'bonus_damage':      '0',
            },
            'sprite_vs_player': {
                'base_damage':       '0',
                'weapon_multiplier': str(self.weapon_multiplier),
                'can_attack':        'true',
                'requires_pvp_mode': 'false',
                'effect':            'none',
            },
            'player_vs_boss': {
                'base_damage':       str(self.base_damage),
                'weapon_multiplier': '1.2',
                'can_attack':        'true',
                'requires_pvp_mode': 'false',
                'effect':            'epic_loot',
                'bonus_damage':      '5',
            },
            'pvp_rules': {
                'friendly_fire':      str(self.friendly_fire).lower(),
                'auto_retaliate':     'false',
                'death_drops_items':  'true',
                'respawn_location':   respawn_room,
                'death_penalty_turns': str(self.death_penalty),
                'combat_cooldown':    '0',
            },
            'damage_types': {k: str(v) for k, v in self.damage_types.items()},
        }
        return sections


# ── SD Config Matrix ─────────────────────────────────────────

@dataclass
class SDConfig:
    """
    Stable Diffusion configuration.
    The prompt style is the visual transformation matrix —
    it maps room descriptions to visual expressions.
    """
    host:           str   = "127.0.0.1"
    port:           int   = 7860
    steps:          int   = 25
    width:          int   = 512
    height:         int   = 512
    cfg:            float = 7.5
    sampler:        str   = "DPM++ 2M"
    scene_suffix:   str   = ""
    negative_prompt: str  = ""
    cache_images:   bool  = True

    def to_ini_sections(self) -> Dict[str, Dict[str, str]]:
        # CRITICAL: section must start with 'SD' — engine uses startswith('SD')
        # host and port MUST be separate keys — engine reads them independently
        return {
            'settings': {
                'default_steps':   str(self.steps),
                'default_width':   str(self.width),
                'default_height':  str(self.height),
                'default_cfg':     str(self.cfg),
                'default_sampler': self.sampler,
                'cache_images':    str(self.cache_images).lower(),
                'image_format':    'jpg',
                'image_quality':   '88',
            },
            'prompt_style': {
                'scene_suffix':    self.scene_suffix,
                'negative_prompt': self.negative_prompt,
            },
            'SD1': {    # ← MUST start with 'SD' — this is enforced here, never user-editable
                'host':    self.host,
                'port':    str(self.port),
                'weight':  '1',
                'timeout': '60',
                'enabled': 'true',
            },
        }


# ── World Config — The Complete Matrix ───────────────────────

@dataclass
class WorldConfig:
    """
    The complete world definition.
    A world is the Cartesian product of its six matrices.
    All cross-references are validated before any file is written.
    """
    world_name:      str
    theme:           WorldTheme
    rooms:           Dict[str, Room]           = field(default_factory=dict)
    objects:         Dict[str, GameObject]     = field(default_factory=dict)
    sprites:         Dict[str, Sprite]         = field(default_factory=dict)
    transformations: Dict[str, Transformation] = field(default_factory=dict)
    combat:          CombatConfig              = field(default_factory=CombatConfig)
    sd_config:       SDConfig                  = field(default_factory=SDConfig)
    physics_applied: List[PhysicsType]         = field(default_factory=list)

    @property
    def room_ids(self) -> Set[str]:
        return set(self.rooms.keys())

    @property
    def object_ids(self) -> Set[str]:
        return set(self.objects.keys())

    @property
    def sprite_ids(self) -> Set[str]:
        return set(self.sprites.keys())

    @property
    def start_room(self) -> Optional[str]:
        for rid, room in self.rooms.items():
            if room.is_start:
                return rid
        return None

    def summary(self) -> str:
        return (f"Rooms:{len(self.rooms)}  Objects:{len(self.objects)}  "
                f"Sprites:{len(self.sprites)}  Transforms:{len(self.transformations)}")
