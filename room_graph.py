"""
N2NHU World Generator - Room Graph Generator
=============================================
Generates guaranteed-connected room graphs of any size.

DIRECTION CONTRACT:
  The generator may ONLY use directions the game engine reads.
  game_engine_rpg.py load_rooms() parses exactly these 6 pairs:
    north/south, east/west, up/down

  northeast/southwest, northwest/southeast, enter/exit are NOT
  read by the engine. Writing them creates rooms with exits that
  the engine silently discards — player ends up "nowhere."

  6 pairs = 12 directional slots per room.
  For any world up to 100 rooms this is more than sufficient.

N2NHU Labs for Applied Artificial Intelligence
"""

import random
from collections import deque
from typing import List, Dict, Tuple, Set, Optional
from world_model import Room, WorldTheme
from theme_engine import ThemeDefaults


# ── Engine-valid direction pairs ONLY ────────────────────────
# These are the EXACT keys game_engine_rpg.py load_rooms() reads.
# DO NOT add northeast/southwest, northwest/southeast, enter/exit —
# the engine will silently drop them, creating unreachable rooms.
DIRECTION_PAIRS = [
    ('north',  'south'),
    ('east',   'west'),
    ('up',     'down'),
]

ALL_DIRECTIONS = [d for pair in DIRECTION_PAIRS for d in pair]


def _safe_id(name: str) -> str:
    return (name.lower()
                .replace(' ', '_')
                .replace("'", '')
                .replace('-', '_')
                .replace('/', '_')
                .replace('(', '')
                .replace(')', '')
                .replace(',', '')
                .replace('.', ''))


def _escape_percent(text: str) -> str:
    import re
    return re.sub(r'(?<!%)%(?!%)', '%%', text)


class RoomGraphGenerator:
    """
    Generates a connected room graph from theme defaults and a target size.
    Every generated graph is guaranteed fully connected via engine-valid directions.
    """

    BONUS_CONNECTION_RATIO = 0.3

    def generate(self,
                 room_count: int,
                 theme_defaults: ThemeDefaults,
                 world_name: str,
                 custom_names: Optional[List[str]] = None) -> Dict[str, Room]:

        room_count = max(3, min(room_count, 100))

        # Step 1: Generate names
        names = self._generate_names(room_count, theme_defaults, custom_names)

        # Step 2: Generate IDs (deduplicated)
        ids = [_safe_id(name) for name in names]
        seen_ids: Dict[str, int] = {}
        unique_ids = []
        for id_ in ids:
            if id_ in seen_ids:
                seen_ids[id_] += 1
                unique_ids.append(f"{id_}_{seen_ids[id_]}")
            else:
                seen_ids[id_] = 0
                unique_ids.append(id_)
        ids = unique_ids

        # Step 3: Build spanning tree — guaranteed connected
        # adjacency[i] = list of (j, direction_from_i, direction_from_j)
        adjacency: Dict[int, List[Tuple[int, str, str]]] = {i: [] for i in range(room_count)}

        connected_indices = {0}
        for i in range(1, room_count):
            # Try all already-connected rooms to find one with a free direction slot
            candidates = list(connected_indices)
            random.shuffle(candidates)
            connected = False
            for target in candidates:
                direction, reverse = self._get_available_direction(adjacency, i, target)
                if direction:
                    adjacency[i].append((target, direction, reverse))
                    adjacency[target].append((i, reverse, direction))
                    connected = True
                    break

            if not connected:
                # All direction slots on all connected rooms are full.
                # Chain: connect i through the most lightly-connected node
                # This keeps the graph valid using only engine directions.
                lightest = min(candidates, key=lambda n: len(adjacency[n]))
                # Remove one existing exit from lightest to free a slot
                # (redirect it via i as intermediate — i becomes a waypoint)
                if adjacency[lightest]:
                    old_j, old_d_from_lightest, old_d_from_j = adjacency[lightest][0]
                    # Remove the old connection
                    adjacency[lightest] = adjacency[lightest][1:]
                    adjacency[old_j] = [(n,d,r) for n,d,r in adjacency[old_j]
                                       if n != lightest]
                    # Now lightest has a free slot — connect to i
                    d1, r1 = self._get_available_direction(adjacency, lightest, i)
                    if d1:
                        adjacency[lightest].append((i, d1, r1))
                        adjacency[i].append((lightest, r1, d1))
                    # Connect i to old_j
                    d2, r2 = self._get_available_direction(adjacency, i, old_j)
                    if d2:
                        adjacency[i].append((old_j, d2, r2))
                        adjacency[old_j].append((i, r2, d2))

            connected_indices.add(i)

        # Step 4: Add bonus connections (loops for exploration interest)
        bonus_count = max(2, int(room_count * self.BONUS_CONNECTION_RATIO))
        attempts = 0
        added = 0
        while added < bonus_count and attempts < bonus_count * 20:
            attempts += 1
            i = random.randint(0, room_count - 1)
            j = random.randint(0, room_count - 1)
            if i == j:
                continue
            already_connected = {t for t, _, _ in adjacency[i]}
            if j in already_connected:
                continue
            direction, reverse = self._get_available_direction(adjacency, i, j)
            if direction:
                adjacency[i].append((j, direction, reverse))
                adjacency[j].append((i, reverse, direction))
                added += 1

        # Step 5: BFS connectivity verification
        reachable = set()
        queue = deque([0])
        while queue:
            current = queue.popleft()
            if current in reachable:
                continue
            reachable.add(current)
            for (neighbor, _, _) in adjacency[current]:
                if neighbor not in reachable:
                    queue.append(neighbor)

        # Force-connect any still-unreachable rooms (safety net)
        unreachable = set(range(room_count)) - reachable
        for idx in unreachable:
            # Try every reachable room until we find one with a free slot
            reachable_list = list(reachable)
            random.shuffle(reachable_list)
            for target in reachable_list:
                direction, reverse = self._get_available_direction(adjacency, idx, target)
                if direction:
                    adjacency[idx].append((target, direction, reverse))
                    adjacency[target].append((idx, reverse, direction))
                    reachable.add(idx)
                    break

        # Step 6: Build Room objects — ONLY engine-valid direction keys in exits dict
        rooms: Dict[str, Room] = {}
        for i in range(room_count):
            room_id   = ids[i]
            room_name = names[i]

            exits = {}
            for (j, direction, _) in adjacency[i]:
                # CRITICAL: only write directions the engine understands
                if direction in ALL_DIRECTIONS:
                    exits[direction] = ids[j]
                # synthetic labels are silently dropped — never written to INI

            description = self._generate_description(room_name, theme_defaults,
                                                     world_name, exits)
            rooms[room_id] = Room(
                room_id     = room_id,
                name        = room_name,
                description = _escape_percent(description),
                exits       = exits,
                is_start    = (i == 0),
            )

        return rooms

    def _get_available_direction(
        self,
        adjacency: Dict[int, List],
        node_a: int,
        node_b: int
    ) -> Tuple[Optional[str], Optional[str]]:
        """Find an unused direction pair between two nodes — engine-valid pairs only."""
        used_from_a = {d for (_, d, _) in adjacency[node_a]}
        used_from_b = {d for (_, d, _) in adjacency[node_b]}

        pairs = DIRECTION_PAIRS.copy()
        random.shuffle(pairs)
        for d_a, d_b in pairs:
            if d_a not in used_from_a and d_b not in used_from_b:
                return d_a, d_b
        return None, None

    def _generate_names(self, count: int, theme: ThemeDefaults,
                        custom_names: Optional[List[str]]) -> List[str]:
        prefixes = theme.suggested_room_prefixes.copy()
        generic = ['Chamber', 'Passage', 'Hall', 'Area', 'Zone',
                   'Room', 'Space', 'Level', 'Section', 'Sector']
        while len(prefixes) < count:
            prefixes.extend(generic)

        random.shuffle(prefixes)
        names = prefixes[:count]

        if custom_names:
            for i, name in enumerate(custom_names[:count]):
                if name.strip():
                    names[i] = name.strip()

        names[0] = 'Entrance'

        # Disambiguate duplicates
        seen: Dict[str, int] = {}
        unique = []
        for name in names:
            if name in seen:
                seen[name] += 1
                unique.append(f"{name} {seen[name]+1}")
            else:
                seen[name] = 0
                unique.append(name)
        return unique

    def _generate_description(self, room_name: str, theme: ThemeDefaults,
                               world_name: str, exits: Dict[str, str]) -> str:
        exit_list = ', '.join(exits.keys()) if exits else 'none'
        templates = [
            (f"The {room_name} of {world_name}. "
             f"A {theme.flavor_adjective} {theme.flavor_noun} with an atmosphere that feels "
             f"entirely in keeping with this place. Exits lead {exit_list}."),
            (f"You stand in the {room_name}. "
             f"Everything here speaks to the {theme.flavor_adjective} nature of {world_name}. "
             f"The air carries traces of what this {theme.flavor_noun} has witnessed. "
             f"Exits: {exit_list}."),
            (f"The {room_name}. In the broader context of {world_name}, "
             f"this space has its own particular character — {theme.flavor_adjective} "
             f"in ways that are immediately apparent. Passages lead {exit_list}."),
        ]
        return random.choice(templates)
