"""
N2NHU World Generator - World Generator Orchestrator
=====================================================
The master compiler. Takes a GeneratorRequest and produces
a validated WorldConfig ready for INI output.

Pipeline:
    Request
      → ThemeEngine          (classify intent → defaults)
      → RoomGraphGenerator   (names + size → connected graph)
      → SpriteFactory        (character names → sprites)
      → PhysicsTemplateLib   (selected physics → transforms + objects)
      → ValidationEngine     (18-check audit — zero invalid guarantee)
      → INIWriter            (WorldConfig → 6 INI files)
      → RoundTripVerifier    (re-read + re-audit written files)

Every stage is independent. Every stage is testable.
The pipeline is the architecture.

N2NHU Labs for Applied Artificial Intelligence
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from world_model import (WorldConfig, WorldTheme, PhysicsType,
                          GameObject, CombatConfig, SDConfig)
from theme_engine import ThemeEngine, ThemeDefaults
from room_graph import RoomGraphGenerator
from sprite_factory import SpriteFactory
from physics_templates import PhysicsTemplateLibrary
from validation_engine import ValidationEngine, RoundTripVerifier
from ini_writer import INIWriter


# ── Generator Request ────────────────────────────────────────

@dataclass
class GeneratorRequest:
    """
    Everything the generator needs — nothing more.
    This is the public API surface. All other internals are hidden.
    """
    world_name:        str
    character_names:   List[str]          = field(default_factory=list)
    room_count:        int                = 20
    physics_types:     List[PhysicsType]  = field(default_factory=list)
    output_dir:        str                = './generated_world'
    custom_theme:      Optional[WorldTheme] = None

    # SD overrides (None = auto from theme)
    sd_host:           str = "127.0.0.1"
    sd_port:           int = 7860
    sd_scene_suffix:   str = ""          # empty = auto
    sd_negative_prompt: str = ""         # empty = auto

    # Advanced overrides
    custom_room_names: List[str]         = field(default_factory=list)
    base_damage_override: Optional[int]  = None


# ── Generator Result ─────────────────────────────────────────

@dataclass
class GeneratorResult:
    """
    The complete output of a generation run.
    Success or failure — fully described.
    """
    success:          bool
    world:            Optional[WorldConfig]
    written_files:    Dict[str, str]      = field(default_factory=dict)
    validation_errors: List[str]          = field(default_factory=list)
    validation_warnings: List[str]        = field(default_factory=list)
    roundtrip_errors: List[str]           = field(default_factory=list)
    summary:          str                 = ""
    theme_used:       Optional[WorldTheme] = None

    def display_summary(self) -> str:
        lines = []
        if self.success:
            lines.append(f"✅  WORLD GENERATED SUCCESSFULLY")
            lines.append(f"    {self.summary}")
            lines.append(f"    Output: {list(self.written_files.values())[0] if self.written_files else 'N/A'}")
            if self.validation_warnings:
                lines.append(f"    ⚠️  {len(self.validation_warnings)} warnings")
        else:
            lines.append(f"❌  GENERATION FAILED")
            for err in self.validation_errors[:5]:
                lines.append(f"    {err}")
            if len(self.validation_errors) > 5:
                lines.append(f"    ... and {len(self.validation_errors)-5} more errors")
        return '\n'.join(lines)


# ── The Generator ────────────────────────────────────────────

class WorldGenerator:
    """
    The N2NHU World Generator.

    One method: generate(request) -> result.
    The entire pipeline in a single call.

    Internally, the pipeline is six independent stages.
    Each stage transforms data. No stage mutates previous stages.
    This IS algebraic architecture.
    """

    def __init__(self):
        self.theme_engine   = ThemeEngine()
        self.room_generator = RoomGraphGenerator()
        self.sprite_factory = SpriteFactory()
        self.physics_lib    = PhysicsTemplateLibrary()
        self.validator      = ValidationEngine()
        self.writer         = INIWriter()
        self.verifier       = RoundTripVerifier()

    def generate(self, request: GeneratorRequest) -> GeneratorResult:
        """
        Execute the complete generation pipeline.
        Returns a GeneratorResult with full audit trail.
        """
        try:
            return self._run_pipeline(request)
        except Exception as e:
            return GeneratorResult(
                success=False,
                world=None,
                validation_errors=[f"Pipeline error: {str(e)}"],
                summary="Generation failed with unexpected error.",
            )

    def _run_pipeline(self, req: GeneratorRequest) -> GeneratorResult:

        # ── STAGE 1: Theme Classification ────────────────────
        theme_defaults = (
            self.theme_engine.get_defaults_for_theme(req.custom_theme)
            if req.custom_theme
            else self.theme_engine.get_defaults(req.world_name)
        )

        # ── STAGE 2: Build WorldConfig shell ─────────────────
        world = WorldConfig(
            world_name = req.world_name,
            theme      = theme_defaults.theme,
        )

        # ── STAGE 3: Room Graph Generation ───────────────────
        world.rooms = self.room_generator.generate(
            room_count   = req.room_count,
            theme_defaults = theme_defaults,
            world_name   = req.world_name,
            custom_names = req.custom_room_names or None,
        )

        # ── STAGE 4: Starter Objects ──────────────────────────
        world.objects = self._build_starter_objects(theme_defaults, world)

        # ── STAGE 5: Physics Template Injection ──────────────
        physics_to_apply = req.physics_types or theme_defaults.default_physics
        for physics_type in physics_to_apply:
            package = self.physics_lib.get_package(physics_type, world, theme_defaults)
            package.inject(world)

        # ── STAGE 6: Sprite Generation ────────────────────────
        if req.character_names:
            world.sprites = self.sprite_factory.generate_sprites(
                names  = req.character_names,
                theme  = theme_defaults,
                world  = world,
            )

        # ── STAGE 7: Combat Config ────────────────────────────
        world.combat = CombatConfig(
            base_damage       = req.base_damage_override or theme_defaults.base_damage,
            respawn_location  = world.start_room or '',
        )

        # ── STAGE 8: SD Config ────────────────────────────────
        world.sd_config = SDConfig(
            host            = req.sd_host,
            port            = req.sd_port,
            scene_suffix    = req.sd_scene_suffix  or theme_defaults.sd_scene_suffix,
            negative_prompt = req.sd_negative_prompt or theme_defaults.sd_negative_prompt,
        )

        # ── STAGE 9: Pre-Write Validation (18 checks) ─────────
        validation = self.validator.validate(world)
        if not validation.is_valid:
            return GeneratorResult(
                success              = False,
                world                = world,
                validation_errors    = validation.errors,
                validation_warnings  = validation.warnings,
                summary              = world.summary(),
                theme_used           = theme_defaults.theme,
            )

        # ── STAGE 10: Write INI Files ─────────────────────────
        written = self.writer.write_all(world, req.output_dir)

        # ── STAGE 11: Round-Trip Verification ─────────────────
        rt_result = self.verifier.verify(req.output_dir, req.world_name)

        return GeneratorResult(
            success              = rt_result.is_valid,
            world                = world,
            written_files        = written,
            validation_errors    = validation.errors + rt_result.errors,
            validation_warnings  = validation.warnings + rt_result.warnings,
            roundtrip_errors     = rt_result.errors,
            summary              = (f"{world.summary()}  |  "
                                    f"Physics: {[p.value for p in world.physics_applied]}"),
            theme_used           = theme_defaults.theme,
        )

    def _build_starter_objects(self, theme: ThemeDefaults,
                                world: WorldConfig) -> Dict[str, GameObject]:
        """
        Build a set of starter objects appropriate to the theme.
        These are present before physics templates add their objects.
        """
        import random
        objects: Dict[str, GameObject] = {}
        room_ids = list(world.rooms.keys())

        if not room_ids:
            return objects

        # Always add: a weapon, a consumable, a key item, a document
        starters = [
            ('starter_weapon', theme.suggested_object_types[0]
             if theme.suggested_object_types else 'weapon',
             True, False, False, theme.base_damage, False, 0, []),

            ('starter_health', 'health item',
             False, True, False, 0, True, 35,
             ['take', 'drop', 'examine', 'use']),

            ('starter_key', 'access key',
             False, False, False, 0, False, 0,
             ['take', 'drop', 'examine', 'use']),

            ('starter_document', 'important document',
             False, False, False, 0, False, 0,
             ['take', 'drop', 'examine', 'read']),
        ]

        for i, (oid, name, is_weapon, is_consumable, is_container,
                damage, health_heal, health_restore, verbs) in enumerate(starters):
            location = room_ids[i % len(room_ids)]
            obj_verbs = verbs or ['take', 'drop', 'examine', 'use']
            if is_weapon:
                obj_verbs = ['take', 'drop', 'examine', 'use', 'attack']

            objects[oid] = GameObject(
                object_id      = oid,
                name           = name,
                description    = (f"A {name} found in this {theme.flavor_adjective} world. "
                                  f"It has a purpose here. Examine it carefully."),
                location       = location,
                takeable       = True,
                is_weapon      = is_weapon,
                damage         = damage,
                is_consumable  = is_consumable,
                health_restore = health_restore,
                is_container   = is_container,
                valid_verbs    = obj_verbs,
            )

        return objects

    def preview(self, request: GeneratorRequest) -> Dict:
        """
        Fast preview — classify theme and return defaults WITHOUT generating files.
        Used by the wizard UI for live preview updates.
        """
        theme = (
            self.theme_engine.get_defaults_for_theme(request.custom_theme)
            if request.custom_theme
            else self.theme_engine.get_defaults(request.world_name)
        )
        return {
            'theme':           theme.theme.value,
            'theme_display':   self.theme_engine.theme_display_name(theme.theme),
            'sd_suffix':       theme.sd_scene_suffix,
            'sd_negative':     theme.sd_negative_prompt,
            'base_damage':     theme.base_damage,
            'default_physics': [p.value for p in theme.default_physics],
            'room_prefixes':   theme.suggested_room_prefixes[:5],
            'flavor':          f"{theme.flavor_adjective} {theme.flavor_noun}",
        }
