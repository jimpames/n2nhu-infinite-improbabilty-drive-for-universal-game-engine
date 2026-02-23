"""
N2NHU World Generator - Validation Engine
==========================================
18-check cross-reference audit. Zero invalid output guarantee.
N2NHU Labs for Applied Artificial Intelligence
"""

import re
import configparser
from collections import deque
from typing import List
from world_model import WorldConfig


class ValidationResult:
    def __init__(self):
        self.errors:   List[str] = []
        self.warnings: List[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str):
        self.errors.append(f"FAIL: {msg}")

    def add_warning(self, msg: str):
        self.warnings.append(f"WARN: {msg}")

    def summary(self) -> str:
        if self.is_valid:
            return f"ALL CLEAN ({len(self.warnings)} warnings)"
        return f"{len(self.errors)} ERRORS  {len(self.warnings)} warnings"


class ValidationEngine:
    def validate(self, world: WorldConfig) -> ValidationResult:
        result    = ValidationResult()
        room_ids   = world.room_ids
        object_ids = world.object_ids

        # 1: Room exit references
        for rid, room in world.rooms.items():
            for direction, target in room.exits.items():
                if target not in room_ids:
                    result.add_error(f"[rooms][{rid}] exit '{direction}'->{target!r} MISSING")

        # 2: Exactly one start room
        starts = [rid for rid, r in world.rooms.items() if r.is_start]
        if len(starts) == 0:
            result.add_error("No start room defined")
        elif len(starts) > 1:
            result.add_error(f"Multiple start rooms: {starts}")

        # 3: BFS connectivity
        if starts and len(world.rooms) > 1:
            reachable = set()
            queue = deque([starts[0]])
            while queue:
                curr = queue.popleft()
                if curr in reachable:
                    continue
                reachable.add(curr)
                if curr in world.rooms:
                    for t in world.rooms[curr].exits.values():
                        if t in room_ids and t not in reachable:
                            queue.append(t)
            for rid in room_ids - reachable:
                result.add_error(f"[rooms][{rid}] UNREACHABLE from start")

        # 4: Room name/description
        for rid, room in world.rooms.items():
            if not room.name.strip():
                result.add_error(f"[rooms][{rid}] missing name")
            if not room.description.strip():
                result.add_error(f"[rooms][{rid}] missing description")

        # 5: Object locations
        for oid, obj in world.objects.items():
            if obj.location and obj.location not in ('none', ''):
                if obj.location not in room_ids and obj.location not in object_ids:
                    result.add_error(f"[objects][{oid}] location={obj.location!r} MISSING")
                elif obj.location in object_ids:
                    if not world.objects[obj.location].is_container:
                        result.add_error(f"[objects][{oid}] location {obj.location!r} not a container")

        # 6: Object name/description
        for oid, obj in world.objects.items():
            if not obj.name.strip():
                result.add_error(f"[objects][{oid}] missing name")
            if not obj.description.strip():
                result.add_error(f"[objects][{oid}] missing description")

        # 7: Sprite spawn_rooms
        for sid, sprite in world.sprites.items():
            for r in sprite.spawn_rooms:
                if r not in room_ids:
                    result.add_error(f"[sprites][{sid}] spawn_room {r!r} MISSING")
            if not sprite.spawn_rooms:
                result.add_warning(f"[sprites][{sid}] has no spawn_rooms")

        # 8: Sprite loot_on_death
        for sid, sprite in world.sprites.items():
            if sprite.loot_on_death and sprite.loot_on_death not in object_ids:
                result.add_error(f"[sprites][{sid}] loot_on_death={sprite.loot_on_death!r} MISSING")

        # 9: Sprite name
        for sid, sprite in world.sprites.items():
            if not sprite.name.strip():
                result.add_error(f"[sprites][{sid}] missing name")

        # 10: Transform object_id
        for tid, t in world.transformations.items():
            if t.object_id not in object_ids:
                result.add_error(f"[transforms][{tid}] object_id={t.object_id!r} MISSING")

        # 11: Transform new_object_id
        for tid, t in world.transformations.items():
            if t.new_object_id and t.new_object_id not in object_ids:
                result.add_error(f"[transforms][{tid}] new_object_id={t.new_object_id!r} MISSING")

        # 12: Transform requires_object
        for tid, t in world.transformations.items():
            if t.requires_object and t.requires_object not in object_ids:
                result.add_error(f"[transforms][{tid}] requires_object={t.requires_object!r} MISSING")
            if t.requires_object_2 and t.requires_object_2 not in object_ids:
                result.add_error(f"[transforms][{tid}] requires_object_2={t.requires_object_2!r} MISSING")

        # 13: Transform new_location
        for tid, t in world.transformations.items():
            if t.new_location and t.new_location not in room_ids:
                result.add_error(f"[transforms][{tid}] new_location={t.new_location!r} MISSING")

        # 14: Combat respawn
        if world.combat.respawn_location and world.combat.respawn_location not in room_ids:
            result.add_error(f"[combat] respawn_location={world.combat.respawn_location!r} MISSING")

        # 15: SD section naming
        for sec in world.sd_config.to_ini_sections():
            if sec not in ('settings', 'prompt_style'):
                if not sec.upper().startswith('SD'):
                    result.add_error(f"[sd] section [{sec}] must start with 'SD'")

        # 16: SD host/port separation
        for sec, data in world.sd_config.to_ini_sections().items():
            if sec not in ('settings', 'prompt_style'):
                if 'url' in data:
                    result.add_error(f"[sd][{sec}] must NOT use combined 'url=' key")
                if 'host' not in data:
                    result.add_error(f"[sd][{sec}] missing 'host' key")
                if 'port' not in data:
                    result.add_error(f"[sd][{sec}] missing 'port' key")

        # 17: Bare % signs
        def check_pct(source, section, key, value):
            if re.search(r'(?<!%)%(?!%)', str(value)):
                result.add_error(f"[{source}][{section}].{key} has bare '%'")

        for rid, room in world.rooms.items():
            for k, v in room.to_ini_section().items():
                check_pct('rooms', rid, k, v)
        for oid, obj in world.objects.items():
            for k, v in obj.to_ini_section().items():
                check_pct('objects', oid, k, v)
        for sid, spr in world.sprites.items():
            for k, v in spr.to_ini_section().items():
                check_pct('sprites', sid, k, v)
        for tid, t in world.transformations.items():
            for k, v in t.to_ini_section().items():
                check_pct('transforms', tid, k, v)

        # 18: Duplicate section IDs
        all_ids = (list(world.room_ids) + list(world.object_ids) +
                   list(world.sprite_ids) + list(world.transformations.keys()))
        seen = set()
        for id_ in all_ids:
            if id_ in seen:
                result.add_error(f"Duplicate section ID '{id_}' across files")
            seen.add(id_)

        return result


class RoundTripVerifier:
    # MUST match game_engine_rpg.py load_rooms() exactly.
    # These are the ONLY directions the engine reads from rooms.ini.
    # Any other direction key written to rooms.ini is silently dropped
    # by the engine, creating rooms with unreachable return paths.
    ENGINE_DIRECTIONS = ['north', 'south', 'east', 'west', 'up', 'down']

    # Directions that look valid but are NOT read by the engine.
    # Writing these creates "nowhere" bugs.
    INVALID_FOR_ENGINE = ['northeast', 'northwest', 'southeast', 'southwest',
                          'enter', 'exit']

    def verify(self, output_dir: str, world_name: str) -> ValidationResult:
        import os
        result = ValidationResult()
        filemap = {
            'rooms':           os.path.join(output_dir, 'rooms.ini'),
            'objects':         os.path.join(output_dir, 'objects.ini'),
            'sprites':         os.path.join(output_dir, 'sprites.ini'),
            'transformations': os.path.join(output_dir, 'transformations.ini'),
            'combat':          os.path.join(output_dir, 'combat.ini'),
            'sd':              os.path.join(output_dir, 'stablediffusion.ini'),
        }
        configs = {}
        for name, path in filemap.items():
            if not os.path.exists(path):
                result.add_error(f"File missing: {path}")
                continue
            c = configparser.RawConfigParser()
            c.read(path)
            configs[name] = c

        if result.errors:
            return result

        rooms   = set(configs['rooms'].sections())
        objects = set(configs['objects'].sections())

        for s in configs['rooms'].sections():
            d = dict(configs['rooms'][s])
            # Valid engine directions — check targets exist
            for dr in self.ENGINE_DIRECTIONS:
                if dr in d and d[dr] not in rooms:
                    result.add_error(
                        f"[rooms][{s}] exit '{dr}'->{d[dr]!r} MISSING after write")
            # Non-engine directions — flag as hard errors
            for dr in self.INVALID_FOR_ENGINE:
                if dr in d:
                    result.add_error(
                        f"[rooms][{s}] exit '{dr}' NOT read by engine "
                        f"(use only: {', '.join(self.ENGINE_DIRECTIONS)})")

        for s in configs['objects'].sections():
            d = dict(configs['objects'][s])
            loc = d.get('location','')
            if loc and loc not in ('none','') and loc not in rooms and loc not in objects:
                result.add_error(f"[objects][{s}] location={loc!r} MISSING after write")

        for s in configs['sprites'].sections():
            d = dict(configs['sprites'][s])
            for r in [x.strip() for x in d.get('spawn_rooms','').split(',') if x.strip()]:
                if r not in rooms:
                    result.add_error(f"[sprites][{s}] spawn_room {r!r} MISSING after write")

        for s in configs['transformations'].sections():
            d = dict(configs['transformations'][s])
            for key in ['object_id','new_object_id','requires_object','requires_object_2']:
                val = d.get(key,'')
                if val and val not in objects:
                    result.add_error(f"[transforms][{s}] {key}={val!r} MISSING after write")

        for sec in [s for s in configs['sd'].sections()
                    if s not in ('settings','prompt_style')]:
            if not sec.upper().startswith('SD'):
                result.add_error(f"[sd][{sec}] not starting with 'SD' after write")

        for name, path in filemap.items():
            with open(path, encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    if re.search(r'(?<!%)%(?!%)', line):
                        result.add_error(f"[{name}] line {i} bare '%' after write")

        return result
