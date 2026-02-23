"""
N2NHU World Generator - Physics Template Library
=================================================
Each physics template is a self-contained package of:
  - Transformation rules (for transformations.ini)
  - Required objects (for objects.ini)

Templates are pure data. Selecting a template injects
pre-validated, cross-referenced rules into the world.
No template can reference an object it doesn't also create.
The algebra is closed.

N2NHU Labs for Applied Artificial Intelligence
"""

from dataclasses import dataclass, field
from typing import List, Dict, Callable
from world_model import (PhysicsType, Transformation, GameObject,
                          WorldTheme, WorldConfig)
from theme_engine import ThemeDefaults
import random


@dataclass
class PhysicsPackage:
    """
    A complete, self-contained physics template.
    Objects and transformations are cross-referenced within the package.
    Injecting a package into a WorldConfig is guaranteed valid.
    """
    physics_type:    PhysicsType
    display_name:    str
    description:     str
    emoji:           str
    objects:         Dict[str, GameObject]     = field(default_factory=dict)
    transformations: Dict[str, Transformation] = field(default_factory=dict)

    def inject(self, world: WorldConfig):
        """Inject this package into a WorldConfig."""
        world.objects.update(self.objects)
        world.transformations.update(self.transformations)
        if self.physics_type not in world.physics_applied:
            world.physics_applied.append(self.physics_type)


class PhysicsTemplateLibrary:
    """
    The complete library of physics templates.
    Each template is a factory that builds a PhysicsPackage
    adapted to the world's theme and room structure.
    """

    def get_package(self,
                    physics_type: PhysicsType,
                    world: WorldConfig,
                    theme: ThemeDefaults) -> PhysicsPackage:
        """Build a physics package for the given type and world context."""
        builders = {
            PhysicsType.TEMPERATURE:   self._build_temperature,
            PhysicsType.ENERGY:        self._build_energy,
            PhysicsType.LOCK_KEY:      self._build_lock_key,
            PhysicsType.CRAFTING:      self._build_crafting,
            PhysicsType.TELEPORTATION: self._build_teleportation,
            PhysicsType.DISGUISE:      self._build_disguise,
            PhysicsType.EXPLOSIVES:    self._build_explosives,
            PhysicsType.BRIBERY:       self._build_bribery,
            PhysicsType.MAGIC:         self._build_magic,
            PhysicsType.MEDICAL:       self._build_medical,
            PhysicsType.GROWTH:        self._build_growth,
            PhysicsType.ALIEN_TECH:    self._build_alien_tech,
        }
        builder = builders.get(physics_type, self._build_lock_key)
        return builder(world, theme)

    def all_packages(self) -> List[Dict]:
        """Return display info for all packages (for UI)."""
        return [
            {'type': PhysicsType.TEMPERATURE,   'emoji': '🧊', 'name': 'Temperature Physics',
             'desc': 'Water freezes, ice melts, fire spreads through temperature zones'},
            {'type': PhysicsType.ENERGY,        'emoji': '⚡', 'name': 'Energy Charging',
             'desc': 'Objects charge in power zones over time (Element 115 style)'},
            {'type': PhysicsType.LOCK_KEY,      'emoji': '🔓', 'name': 'Lock & Key',
             'desc': 'Doors and containers require keys or combinations'},
            {'type': PhysicsType.CRAFTING,      'emoji': '🧪', 'name': 'Crafting / Combining',
             'desc': 'Combine two objects to create a third'},
            {'type': PhysicsType.TELEPORTATION, 'emoji': '🚀', 'name': 'Teleportation',
             'desc': 'Portals and launch consoles transport players between locations'},
            {'type': PhysicsType.DISGUISE,      'emoji': '🎭', 'name': 'Disguise System',
             'desc': 'Wearing disguises changes how enemies react to you'},
            {'type': PhysicsType.EXPLOSIVES,    'emoji': '💣', 'name': 'Timed Explosives',
             'desc': 'Place charges, arm timer, detonate from safe distance'},
            {'type': PhysicsType.BRIBERY,       'emoji': '🗝️', 'name': 'Bribery / Persuasion',
             'desc': 'Items that neutralize hostile sprites when offered'},
            {'type': PhysicsType.MAGIC,         'emoji': '✨', 'name': 'Magic Casting',
             'desc': 'Spell words transform rooms and objects'},
            {'type': PhysicsType.MEDICAL,       'emoji': '🏥', 'name': 'Medical System',
             'desc': 'Heal wounded characters, perform procedures, use supplies'},
            {'type': PhysicsType.GROWTH,        'emoji': '🌱', 'name': 'Growth / Decay',
             'desc': 'Plants grow, food spoils, wounds heal over time'},
            {'type': PhysicsType.ALIEN_TECH,    'emoji': '🛸', 'name': 'Alien Technology',
             'desc': 'Scan and activate alien artifacts through multi-step sequences'},
        ]

    def _first_room_id(self, world: WorldConfig) -> str:
        return world.start_room or list(world.rooms.keys())[0]

    def _random_room(self, world: WorldConfig) -> str:
        return random.choice(list(world.rooms.keys()))

    # ── TEMPLATE BUILDERS ────────────────────────────────────

    def _build_energy(self, world: WorldConfig, theme: ThemeDefaults) -> PhysicsPackage:
        room = self._random_room(world)
        pkg = PhysicsPackage(
            physics_type = PhysicsType.ENERGY,
            display_name = 'Energy Charging',
            description  = 'Objects charge in power zones over time',
            emoji        = '⚡',
        )
        pkg.objects['power_cell_inert'] = GameObject(
            object_id   = 'power_cell_inert',
            name        = 'inert power cell',
            description = ('A power cell in its inert state. It requires a power zone '
                           'to become energized. Handle with care.'),
            location    = self._random_room(world),
            takeable    = True,
            valid_verbs = ['take', 'drop', 'examine', 'use', 'insert'],
        )
        pkg.objects['power_cell_charged'] = GameObject(
            object_id   = 'power_cell_charged',
            name        = 'charged power cell',
            description = ('A fully energized power cell, humming with contained power. '
                           'It glows faintly and is warm to the touch.'),
            location    = 'none',
            takeable    = True,
            valid_verbs = ['take', 'drop', 'examine', 'use', 'insert'],
        )
        pkg.transformations['energy_charge'] = Transformation(
            transform_id      = 'energy_charge',
            object_id         = 'power_cell_inert',
            state             = 'normal',
            turns_required    = 5,
            new_state         = 'charged',
            new_object_id     = 'power_cell_charged',
            location_property = 'power_zone',
            message           = ('The power cell begins to absorb energy from the zone. '
                                 'After several moments the humming intensifies and the '
                                 'cell glows with stored power. It is fully charged.'),
        )
        # Mark a room as power_zone
        if room in world.rooms:
            world.rooms[room].properties['power_zone'] = 'true'
        return pkg

    def _build_lock_key(self, world: WorldConfig, theme: ThemeDefaults) -> PhysicsPackage:
        room_ids = list(world.rooms.keys())
        locked_room = room_ids[min(2, len(room_ids)-1)]  # third room
        pkg = PhysicsPackage(
            physics_type = PhysicsType.LOCK_KEY,
            display_name = 'Lock & Key',
            description  = 'Doors and containers require keys',
            emoji        = '🔓',
        )
        pkg.objects['master_key'] = GameObject(
            object_id   = 'master_key',
            name        = 'master key',
            description = ('A heavy key that opens the locked door. '
                           'Someone left it here — either careless or confident '
                           'that you would never find it.'),
            location    = self._random_room(world),
            takeable    = True,
            valid_verbs = ['take', 'drop', 'examine', 'use'],
        )
        pkg.transformations['door_unlocked'] = Transformation(
            transform_id   = 'door_unlocked',
            object_id      = 'master_key',
            state          = 'normal',
            turns_required = 1,
            new_state      = 'used',
            message        = ('The key fits. The lock disengages with a heavy clunk. '
                              'The door swings open. Whatever was locked away is now accessible.'),
        )
        if locked_room in world.rooms:
            world.rooms[locked_room].properties['locked'] = 'true'
        return pkg

    def _build_crafting(self, world: WorldConfig, theme: ThemeDefaults) -> PhysicsPackage:
        pkg = PhysicsPackage(
            physics_type = PhysicsType.CRAFTING,
            display_name = 'Crafting / Combining',
            description  = 'Combine objects to create new ones',
            emoji        = '🧪',
        )
        pkg.objects['ingredient_a'] = GameObject(
            object_id   = 'ingredient_a',
            name        = 'component A',
            description = ('One half of a combination. Alone it does little. '
                           'Combined with the right partner, it becomes something more.'),
            location    = self._random_room(world),
            takeable    = True,
            valid_verbs = ['take', 'drop', 'examine', 'use'],
        )
        pkg.objects['ingredient_b'] = GameObject(
            object_id   = 'ingredient_b',
            name        = 'component B',
            description = ('The complementary component. There is a satisfaction '
                           'in finding the thing that completes another thing.'),
            location    = self._random_room(world),
            takeable    = True,
            valid_verbs = ['take', 'drop', 'examine', 'use'],
        )
        pkg.objects['crafted_result'] = GameObject(
            object_id     = 'crafted_result',
            name          = 'combined item',
            description   = ('The result of combining components A and B. '
                             'Something new exists that did not exist before. '
                             'This is the point of crafting.'),
            location      = 'none',
            takeable      = True,
            is_consumable = True,
            health_restore = 30,
            valid_verbs   = ['take', 'drop', 'examine', 'use'],
        )
        pkg.transformations['craft_combine'] = Transformation(
            transform_id   = 'craft_combine',
            object_id      = 'ingredient_a',
            state          = 'normal',
            turns_required = 1,
            new_state      = 'combined',
            new_object_id  = 'crafted_result',
            requires_object = 'ingredient_b',
            message        = ('You combine the two components. There is a moment of '
                              'uncertainty and then — yes. The combined item exists. '
                              'It is more than the sum of its parts.'),
        )
        return pkg

    def _build_explosives(self, world: WorldConfig, theme: ThemeDefaults) -> PhysicsPackage:
        pkg = PhysicsPackage(
            physics_type = PhysicsType.EXPLOSIVES,
            display_name = 'Timed Explosives',
            description  = 'Place charges, arm, detonate',
            emoji        = '💣',
        )
        pkg.objects['explosive_charge'] = GameObject(
            object_id   = 'explosive_charge',
            name        = 'explosive charge',
            description = ('A shaped explosive charge. Treat with appropriate respect. '
                           'Requires a detonator to activate. Place at the target, '
                           'arm with the detonator, move to safe distance.'),
            location    = self._random_room(world),
            takeable    = True,
            is_weapon   = True,
            damage      = 80,
            valid_verbs = ['take', 'drop', 'examine', 'use', 'place'],
        )
        pkg.objects['detonator'] = GameObject(
            object_id   = 'detonator',
            name        = 'detonator',
            description = ('A remote detonation device. Works at range. '
                           'Press when clear of the blast radius.'),
            location    = self._random_room(world),
            takeable    = True,
            valid_verbs = ['take', 'drop', 'examine', 'use'],
        )
        pkg.transformations['arm_explosive'] = Transformation(
            transform_id    = 'arm_explosive',
            object_id       = 'explosive_charge',
            state           = 'placed',
            turns_required  = 1,
            new_state       = 'armed',
            requires_object = 'detonator',
            message         = ('You connect the detonator. A small LED blinks red. '
                               'The charge is armed. Time to move.'),
        )
        pkg.transformations['detonate'] = Transformation(
            transform_id   = 'detonate',
            object_id      = 'explosive_charge',
            state          = 'armed',
            turns_required = 3,
            new_state      = 'detonated',
            message        = ('The explosion is larger than expected. The structural '
                              'damage is extensive. The objective is achieved. '
                              'Mission success.'),
        )
        return pkg

    def _build_disguise(self, world: WorldConfig, theme: ThemeDefaults) -> PhysicsPackage:
        pkg = PhysicsPackage(
            physics_type = PhysicsType.DISGUISE,
            display_name = 'Disguise System',
            description  = 'Wear disguises to change NPC reactions',
            emoji        = '🎭',
        )
        pkg.objects['disguise_item'] = GameObject(
            object_id   = 'disguise_item',
            name        = 'disguise',
            description = ('A convincing disguise. Put it on and the world sees '
                           'someone different. Being someone else, even briefly, '
                           'changes what is possible.'),
            location    = self._random_room(world),
            takeable    = True,
            is_wearable = True,
            valid_verbs = ['take', 'drop', 'examine', 'wear', 'use'],
        )
        pkg.transformations['wear_disguise'] = Transformation(
            transform_id   = 'wear_disguise',
            object_id      = 'disguise_item',
            state          = 'normal',
            turns_required = 1,
            new_state      = 'wearing',
            message        = ('You put on the disguise. You look in the nearest '
                              'reflective surface and see someone else entirely. '
                              'The transformation is complete. Act the part.'),
        )
        return pkg

    def _build_bribery(self, world: WorldConfig, theme: ThemeDefaults) -> PhysicsPackage:
        pkg = PhysicsPackage(
            physics_type = PhysicsType.BRIBERY,
            display_name = 'Bribery / Persuasion',
            description  = 'Items that neutralize hostile sprites',
            emoji        = '🗝️',
        )
        pkg.objects['bribe_item'] = GameObject(
            object_id      = 'bribe_item',
            name           = 'bribe',
            description    = ('Something that everyone wants. Currency is fungible '
                              'but desire is specific. This is the right currency '
                              'for this particular situation.'),
            location       = self._random_room(world),
            takeable       = True,
            is_consumable  = True,
            health_restore = 0,
            bribe_value    = 'high',
            valid_verbs    = ['take', 'drop', 'examine', 'use', 'give'],
        )
        pkg.transformations['bribe_used'] = Transformation(
            transform_id   = 'bribe_used',
            object_id      = 'bribe_item',
            state          = 'normal',
            turns_required = 1,
            new_state      = 'consumed',
            message        = ('You offer the bribe. There is a moment — calculation '
                              'behind their eyes — and then acceptance. They look away. '
                              'You have purchased temporary blindness. Use it well.'),
        )
        return pkg

    def _build_medical(self, world: WorldConfig, theme: ThemeDefaults) -> PhysicsPackage:
        pkg = PhysicsPackage(
            physics_type = PhysicsType.MEDICAL,
            display_name = 'Medical System',
            description  = 'Heal wounded, perform procedures',
            emoji        = '🏥',
        )
        pkg.objects['medical_kit'] = GameObject(
            object_id      = 'medical_kit',
            name           = 'medical kit',
            description    = ('A field medical kit containing the essentials. '
                              'Not everything, but enough. In the right hands '
                              'it is more powerful than any weapon here.'),
            location       = self._random_room(world),
            takeable       = True,
            is_consumable  = True,
            health_restore = 40,
            valid_verbs    = ['take', 'drop', 'examine', 'use'],
        )
        pkg.objects['advanced_medicine'] = GameObject(
            object_id      = 'advanced_medicine',
            name           = 'advanced medicine',
            description    = ('High-grade medical supplies. Requires skill to use '
                              'correctly. In the right hands, recovers what seemed lost.'),
            location       = self._random_room(world),
            takeable       = True,
            is_consumable  = True,
            health_restore = 70,
            valid_verbs    = ['take', 'drop', 'examine', 'use'],
        )
        pkg.transformations['apply_treatment'] = Transformation(
            transform_id   = 'apply_treatment',
            object_id      = 'medical_kit',
            state          = 'normal',
            turns_required = 2,
            new_state      = 'used',
            message        = ('You apply the treatment with care and precision. '
                              'The improvement is immediate. There is no more '
                              'reliable satisfaction than healing working as intended.'),
        )
        return pkg

    def _build_magic(self, world: WorldConfig, theme: ThemeDefaults) -> PhysicsPackage:
        pkg = PhysicsPackage(
            physics_type = PhysicsType.MAGIC,
            display_name = 'Magic Casting',
            description  = 'Spell words transform rooms and objects',
            emoji        = '✨',
        )
        pkg.objects['spell_scroll'] = GameObject(
            object_id   = 'spell_scroll',
            name        = 'spell scroll',
            description = ('A scroll containing an incantation. The words are '
                           'precise — power without precision is just noise. '
                           'Read the words correctly and something changes.'),
            location    = self._random_room(world),
            takeable    = True,
            valid_verbs = ['take', 'drop', 'examine', 'read', 'cast', 'use'],
        )
        pkg.objects['enchanted_item'] = GameObject(
            object_id   = 'enchanted_item',
            name        = 'enchanted item',
            description = ('An object altered by magical means. It is the same '
                           'object it was and also entirely different. '
                           'Magic specializes in this kind of paradox.'),
            location    = 'none',
            takeable    = True,
            valid_verbs = ['take', 'drop', 'examine', 'use'],
        )
        pkg.transformations['cast_spell'] = Transformation(
            transform_id    = 'cast_spell',
            object_id       = 'spell_scroll',
            state           = 'normal',
            turns_required  = 1,
            new_state       = 'cast',
            new_object_id   = 'enchanted_item',
            message         = ('The words of the incantation form and release. '
                               'There is a moment where the laws of the world '
                               'negotiate with the instruction you have just given them. '
                               'The spell takes effect.'),
        )
        return pkg

    def _build_teleportation(self, world: WorldConfig, theme: ThemeDefaults) -> PhysicsPackage:
        rooms = list(world.rooms.keys())
        dest_room = rooms[-1] if len(rooms) > 1 else rooms[0]
        pkg = PhysicsPackage(
            physics_type = PhysicsType.TELEPORTATION,
            display_name = 'Teleportation',
            description  = 'Portal devices transport players between locations',
            emoji        = '🚀',
        )
        pkg.objects['portal_device'] = GameObject(
            object_id   = 'portal_device',
            name        = 'portal device',
            description = ('A device that folds space. The destination is encoded '
                           'in its configuration. Activate it and you are somewhere '
                           'else. The transition is instantaneous and profoundly disorienting.'),
            location    = self._random_room(world),
            takeable    = True,
            valid_verbs = ['take', 'drop', 'examine', 'activate', 'use'],
        )
        pkg.transformations['teleport_activate'] = Transformation(
            transform_id   = 'teleport_activate',
            object_id      = 'portal_device',
            state          = 'normal',
            turns_required = 1,
            new_state      = 'activated',
            new_location   = dest_room,
            message        = ('You activate the device. Space folds. You are '
                              f'somewhere else entirely. You are in the '
                              f'{world.rooms[dest_room].name}.'),
        )
        return pkg

    def _build_temperature(self, world: WorldConfig, theme: ThemeDefaults) -> PhysicsPackage:
        pkg = PhysicsPackage(
            physics_type = PhysicsType.TEMPERATURE,
            display_name = 'Temperature Physics',
            description  = 'Water freezes, ice melts, temperature zones affect objects',
            emoji        = '🧊',
        )
        pkg.objects['water_container'] = GameObject(
            object_id   = 'water_container',
            name        = 'container of water',
            description = 'Water in a container. Its state depends entirely on temperature.',
            location    = self._random_room(world),
            takeable    = True,
            valid_verbs = ['take', 'drop', 'examine', 'use'],
        )
        pkg.objects['ice_block'] = GameObject(
            object_id   = 'ice_block',
            name        = 'block of ice',
            description = ('Frozen water. In a cold zone it stays frozen. '
                           'Elsewhere it will return to what it was.'),
            location    = 'none',
            takeable    = True,
            valid_verbs = ['take', 'drop', 'examine', 'use'],
        )
        pkg.transformations['water_freezes'] = Transformation(
            transform_id      = 'water_freezes',
            object_id         = 'water_container',
            state             = 'normal',
            turns_required    = 3,
            new_state         = 'frozen',
            new_object_id     = 'ice_block',
            location_property = 'cold_zone',
            message           = ('The water in the container begins to crystallize. '
                                 'The temperature here is doing exactly what temperature does. '
                                 'The container now holds a solid block of ice.'),
        )
        pkg.transformations['ice_melts'] = Transformation(
            transform_id      = 'ice_melts',
            object_id         = 'ice_block',
            state             = 'frozen',
            turns_required    = 4,
            new_state         = 'normal',
            new_object_id     = 'water_container',
            location_property = 'warm_zone',
            message           = ('The ice block softens. Drops form. The solid becomes '
                                 'liquid again with the unhurried patience of physics '
                                 'doing what physics does.'),
        )
        return pkg

    def _build_growth(self, world: WorldConfig, theme: ThemeDefaults) -> PhysicsPackage:
        pkg = PhysicsPackage(
            physics_type = PhysicsType.GROWTH,
            display_name = 'Growth / Decay',
            description  = 'Plants grow, food spoils over time',
            emoji        = '🌱',
        )
        pkg.objects['seed'] = GameObject(
            object_id   = 'seed',
            name        = 'seed',
            description = ('A seed. Contains the complete instructions for becoming '
                           'something much larger. Currently not using any of them.'),
            location    = self._random_room(world),
            takeable    = True,
            valid_verbs = ['take', 'drop', 'examine', 'plant', 'use'],
        )
        pkg.objects['grown_plant'] = GameObject(
            object_id      = 'grown_plant',
            name           = 'grown plant',
            description    = ('The seed followed its instructions. It is now a plant. '
                              'This is what seeds do when given time and a suitable location.'),
            location       = 'none',
            takeable       = True,
            is_consumable  = True,
            health_restore = 20,
            valid_verbs    = ['take', 'drop', 'examine', 'eat', 'use'],
        )
        pkg.transformations['seed_grows'] = Transformation(
            transform_id   = 'seed_grows',
            object_id      = 'seed',
            state          = 'planted',
            turns_required = 8,
            new_state      = 'grown',
            new_object_id  = 'grown_plant',
            message        = ('The seed has grown. It took time — eight turns, to be '
                              'precise — but the instructions encoded in the seed have '
                              'been executed faithfully. A plant exists where there was none.'),
        )
        return pkg

    def _build_alien_tech(self, world: WorldConfig, theme: ThemeDefaults) -> PhysicsPackage:
        pkg = PhysicsPackage(
            physics_type = PhysicsType.ALIEN_TECH,
            display_name = 'Alien Technology',
            description  = 'Scan and activate alien artifacts',
            emoji        = '🛸',
        )
        pkg.objects['alien_artifact'] = GameObject(
            object_id   = 'alien_artifact',
            name        = 'alien artifact',
            description = ('An object not made by human hands. The materials are '
                           'unidentifiable. The purpose is unclear. The craftsmanship '
                           'is either primitive or so advanced it looks primitive.'),
            location    = self._random_room(world),
            takeable    = True,
            valid_verbs = ['take', 'drop', 'examine', 'scan', 'activate', 'use'],
        )
        pkg.objects['scanner_device'] = GameObject(
            object_id   = 'scanner_device',
            name        = 'scanner device',
            description = ('A scanning device that analyzes non-terrestrial objects. '
                           'Point at artifact. Read output. Repeat until understanding '
                           'approaches something resembling certainty.'),
            location    = self._random_room(world),
            takeable    = True,
            valid_verbs = ['take', 'drop', 'examine', 'scan', 'use'],
        )
        pkg.objects['activated_artifact'] = GameObject(
            object_id   = 'activated_artifact',
            name        = 'activated alien artifact',
            description = ('The artifact is doing something now. What it is doing '
                           'is difficult to describe precisely. The effect is '
                           'measurable even if the mechanism is not understood.'),
            location    = 'none',
            takeable    = True,
            valid_verbs = ['take', 'drop', 'examine', 'use'],
        )
        pkg.transformations['alien_scan'] = Transformation(
            transform_id    = 'alien_scan',
            object_id       = 'alien_artifact',
            state           = 'dormant',
            turns_required  = 2,
            new_state       = 'analyzed',
            requires_object = 'scanner_device',
            message         = ('The scanner reads the artifact. The output is a cascade '
                               'of data that means something to someone who understands it. '
                               'You understand enough to proceed to activation.'),
        )
        pkg.transformations['alien_activate'] = Transformation(
            transform_id   = 'alien_activate',
            object_id      = 'alien_artifact',
            state          = 'analyzed',
            turns_required = 1,
            new_state      = 'active',
            new_object_id  = 'activated_artifact',
            message        = ('The artifact activates. The change is immediate and '
                              'unmistakable. You have caused something non-human to '
                              'do what it was built to do. This feels significant.'),
        )
        return pkg
