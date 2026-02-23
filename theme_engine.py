"""
N2NHU World Generator - Theme Engine
======================================
Translates a world name into a complete set of configuration defaults.
This is the intelligence layer — from one string, it derives dozens
of calibrated parameters across all six output files.

The theme engine is a pure function: WorldName → ThemeDefaults.
No side effects. No state. Input → Output.

N2NHU Labs for Applied Artificial Intelligence
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from world_model import WorldTheme, PhysicsType, AIBehavior


@dataclass
class ThemeDefaults:
    """
    Complete set of defaults derived from world theme classification.
    Every field has a value. Nothing is None. The engine always has
    a complete configuration to work with.
    """
    theme:              WorldTheme
    sd_scene_suffix:    str
    sd_negative_prompt: str

    # Combat scalars
    base_damage:        int
    sprite_aggression_low:  float   # for non-hostile sprites
    sprite_aggression_high: float   # for hostile sprites
    boss_health:        int
    minion_health:      int

    # World structure defaults
    suggested_room_prefixes: List[str]
    suggested_object_types:  List[str]
    default_physics:         List[PhysicsType]
    suggested_verbs_extra:   List[str]

    # Tone
    flavor_adjective:   str     # used in auto-generated descriptions
    flavor_noun:        str     # used in auto-generated descriptions


# ── Theme Classification Table ───────────────────────────────
# This IS the theme engine. A pure data structure.
# Adding a new theme is adding rows to this table. No code changes.

THEME_KEYWORDS: List[Tuple[WorldTheme, List[str]]] = [
    (WorldTheme.SCIFI,     ['area 51', 'alien', 'space', 'star trek', 'galaxy',
                            'mars', 'ufo', 'nasa', 'robot', 'android', 'scifi',
                            'sci-fi', 'stargate', 'battlestar', 'moon', 'orbit',
                            'cosmic', 'nebula', 'federation', 'empire']),

    (WorldTheme.MILITARY,  ['mash', 'hogan', 'stalag', 'army', 'combat', 'war',
                            'military', 'soldier', 'battalion', 'platoon', 'fort',
                            'barracks', 'mission impossible', 'a-team', 'seal',
                            'ranger', 'special ops', 'frontline', 'vietnam',
                            'korean', 'wwii', 'ww2', 'normandy', 'patrol']),

    (WorldTheme.FANTASY,   ['hogwarts', 'wizard', 'dragon', 'medieval', 'castle',
                            'zork', 'dungeon', 'magic', 'elf', 'dwarf', 'sword',
                            'quest', 'realm', 'kingdom', 'sorcerer', 'witch',
                            'enchanted', 'fantasy', 'rpg', 'adventure', 'hero']),

    (WorldTheme.DOMESTIC,  ['barbie', 'full house', 'brady', 'family', 'home',
                            'house', 'suburb', 'kitchen', 'cozy', 'domestic',
                            'sitcom', 'neighborhood', 'school', 'mall', 'shop',
                            'bakery', 'cafe', 'dollhouse', 'dream house']),

    (WorldTheme.HORROR,    ['haunted', 'halloween', 'dracula', 'vampire', 'zombie',
                            'horror', 'ghost', 'dark', 'mansion', 'cemetery',
                            'asylum', 'cursed', 'forbidden', 'cthulhu', 'evil',
                            'nightmare', 'terror', 'shadow', 'silent hill']),

    (WorldTheme.ADVENTURE, ['indiana jones', 'pirate', 'jungle', 'explorer',
                            'treasure', 'expedition', 'safari', 'island', 'temple',
                            'ruins', 'artifact', 'archaeology', 'map', 'tomb',
                            'raiders', 'national treasure', 'uncharted']),

    (WorldTheme.SITCOM,    ['bewitched', 'i love lucy', 'gilligan', 'cheers',
                            'seinfeld', 'friends', 'office', 'parks', 'frasier',
                            'taxi', 'mork', 'three company', 'laverne', 'happy days',
                            'fonzie', 'sam malone', 'norm', 'cliff']),

    (WorldTheme.DISCO,     ['studio 54', 'disco', 'dance club', 'nightclub', 'dance floor',
                            'saturday night fever', 'dance hall', 'roller rink', 'boogie',
                            'dj', 'turntable', 'rave', 'club night', 'discotheque']),

    (WorldTheme.NIGHTCLUB, ['bar', 'nightclub', 'lounge', 'speakeasy', 'jazz club',
                            'cocktail', 'vip lounge', 'rooftop bar', 'cabaret',
                            'burlesque', 'velvet rope', 'bouncer', 'bartender']),

    (WorldTheme.CRIME_SPY, ['james bond', 'spy', 'agent', 'cia', 'mi6', 'fbi',
                            'detective', 'noir', 'mystery', 'crime', 'heist',
                            'get smart', 'man from uncle', 'magnum', 'columbo',
                            'sherlock', 'poirot', 'morse', ' hitman']),
]


THEME_DEFAULTS: Dict[WorldTheme, ThemeDefaults] = {

    WorldTheme.SCIFI: ThemeDefaults(
        theme               = WorldTheme.SCIFI,
        sd_scene_suffix     = ('classified military installation, alien technology, '
                               'science fiction, cinematic lighting, photorealistic, '
                               'highly detailed, atmospheric, dramatic shadows, 8k quality'),
        sd_negative_prompt  = ('blurry, low quality, distorted, fantasy, medieval, magic, '
                               'dragons, swords, cartoon, anime, text, watermark, stock photo, logo, signature, fake text, alamy, shutterstock, getty, letters, '
                               'cobblestone, torch, forest, dungeon'),
        base_damage             = 22,
        sprite_aggression_low   = 0.15,
        sprite_aggression_high  = 0.75,
        boss_health             = 150,
        minion_health           = 55,
        suggested_room_prefixes = ['Laboratory', 'Control Room', 'Hangar', 'Corridor',
                                   'Reactor Chamber', 'Observation Deck', 'Launch Bay',
                                   'Quarantine Zone', 'Archive Vault', 'Engineering Bay'],
        suggested_object_types  = ['energy_cell', 'scanner', 'access_card', 'data_pad',
                                   'plasma_rifle', 'alien_artifact', 'radiation_suit'],
        default_physics         = [PhysicsType.ENERGY, PhysicsType.TELEPORTATION,
                                   PhysicsType.ALIEN_TECH],
        suggested_verbs_extra   = ['scan', 'activate', 'insert', 'launch', 'program'],
        flavor_adjective        = 'classified',
        flavor_noun             = 'installation',
    ),

    WorldTheme.MILITARY: ThemeDefaults(
        theme               = WorldTheme.MILITARY,
        sd_scene_suffix     = ('military camp, wartime, soldiers, olive drab, '
                               'cinematic, dramatic lighting, photorealistic, '
                               'historical, war drama, gritty realistic'),
        sd_negative_prompt  = ('blurry, low quality, fantasy, aliens, futuristic, '
                               'modern technology, cartoon, anime, text, watermark, stock photo, logo, signature, fake text, alamy, shutterstock, getty, letters, '
                               'clean, pristine, comfortable, colorful'),
        base_damage             = 20,
        sprite_aggression_low   = 0.2,
        sprite_aggression_high  = 0.8,
        boss_health             = 120,
        minion_health           = 50,
        suggested_room_prefixes = ['Barracks', 'Command Post', 'Motor Pool', 'Mess Hall',
                                   'Infirmary', 'Armory', 'Briefing Room', 'Guard Post',
                                   'Supply Depot', 'Communications Center'],
        suggested_object_types  = ['rifle', 'ration', 'dog_tags', 'map', 'radio',
                                   'explosive', 'medkit', 'binoculars', 'uniform'],
        default_physics         = [PhysicsType.EXPLOSIVES, PhysicsType.MEDICAL,
                                   PhysicsType.DISGUISE],
        suggested_verbs_extra   = ['attack', 'radio', 'report', 'defuse', 'treat'],
        flavor_adjective        = 'battle-worn',
        flavor_noun             = 'outpost',
    ),

    WorldTheme.FANTASY: ThemeDefaults(
        theme               = WorldTheme.FANTASY,
        sd_scene_suffix     = ('fantasy RPG environment, medieval, atmospheric lighting, '
                               'cinematic, detailed, stone walls, torchlight, '
                               'mystical, high quality, dramatic'),
        sd_negative_prompt  = ('blurry, low quality, distorted, modern, futuristic, '
                               'cartoon, anime, text, watermark, stock photo, logo, signature, fake text, alamy, shutterstock, getty, letters, alien, sci-fi'),
        base_damage             = 18,
        sprite_aggression_low   = 0.2,
        sprite_aggression_high  = 0.7,
        boss_health             = 130,
        minion_health           = 45,
        suggested_room_prefixes = ['Great Hall', 'Dungeon', 'Tower', 'Library', 'Chapel',
                                   'Armory', 'Throne Room', 'Garden', 'Crypt', 'Tavern'],
        suggested_object_types  = ['sword', 'scroll', 'potion', 'key', 'torch',
                                   'spell_book', 'amulet', 'gold_coins', 'lockpick'],
        default_physics         = [PhysicsType.MAGIC, PhysicsType.LOCK_KEY,
                                   PhysicsType.CRAFTING],
        suggested_verbs_extra   = ['cast', 'read', 'pray', 'enchant', 'forge'],
        flavor_adjective        = 'ancient',
        flavor_noun             = 'realm',
    ),

    WorldTheme.DOMESTIC: ThemeDefaults(
        theme               = WorldTheme.DOMESTIC,
        sd_scene_suffix     = ('bright cheerful interior, pastel colors, cozy home, '
                               'soft lighting, photorealistic, detailed, warm atmosphere, '
                               'inviting, lifestyle photography quality'),
        sd_negative_prompt  = ('blurry, low quality, dark, scary, violent, weapons, '
                               'military, aliens, medieval, cartoon, anime, text, '
                               'watermark, stock photo, logo, signature, fake text, alamy, shutterstock, getty, letters, gritty, dangerous'),
        base_damage             = 5,
        sprite_aggression_low   = 0.05,
        sprite_aggression_high  = 0.2,
        boss_health             = 60,
        minion_health           = 30,
        suggested_room_prefixes = ['Living Room', 'Kitchen', 'Bedroom', 'Backyard',
                                   'Garage', 'Basement', 'Attic', 'Dining Room',
                                   'Fashion Studio', 'Dream Closet'],
        suggested_object_types  = ['fashion_item', 'food', 'gift', 'toy', 'phone',
                                   'outfit', 'accessory', 'recipe', 'photo'],
        default_physics         = [PhysicsType.CRAFTING, PhysicsType.GROWTH],
        suggested_verbs_extra   = ['wear', 'cook', 'give', 'call', 'decorate'],
        flavor_adjective        = 'cheerful',
        flavor_noun             = 'home',
    ),

    WorldTheme.HORROR: ThemeDefaults(
        theme               = WorldTheme.HORROR,
        sd_scene_suffix     = ('horror, dark atmosphere, shadows, eerie lighting, '
                               'photorealistic, detailed, fog, abandoned, decaying, '
                               'cinematic horror, dramatic chiaroscuro'),
        sd_negative_prompt  = ('blurry, low quality, bright, cheerful, colorful, '
                               'cartoon, anime, text, watermark, stock photo, logo, signature, fake text, alamy, shutterstock, getty, letters, modern, clean, '
                               'comfortable, futuristic'),
        base_damage             = 25,
        sprite_aggression_low   = 0.3,
        sprite_aggression_high  = 0.9,
        boss_health             = 160,
        minion_health           = 60,
        suggested_room_prefixes = ['Foyer', 'Library', 'Cellar', 'Attic', 'Crypt',
                                   'Laboratory', 'Chapel', 'Ballroom', 'Servants Quarters',
                                   'Hidden Room'],
        suggested_object_types  = ['candle', 'journal', 'crucifix', 'key', 'photograph',
                                   'ritual_item', 'weapon', 'potion', 'map'],
        default_physics         = [PhysicsType.LOCK_KEY, PhysicsType.MAGIC,
                                   PhysicsType.TEMPERATURE],
        suggested_verbs_extra   = ['hide', 'flee', 'investigate', 'banish', 'pray'],
        flavor_adjective        = 'cursed',
        flavor_noun             = 'darkness',
    ),

    WorldTheme.ADVENTURE: ThemeDefaults(
        theme               = WorldTheme.ADVENTURE,
        sd_scene_suffix     = ('adventure, exploration, jungle, ancient ruins, '
                               'cinematic, dramatic lighting, photorealistic, '
                               'detailed, atmospheric, discovery'),
        sd_negative_prompt  = ('blurry, low quality, modern, urban, sci-fi, '
                               'cartoon, anime, text, watermark, stock photo, logo, signature, fake text, alamy, shutterstock, getty, letters, alien, fantasy magic'),
        base_damage             = 20,
        sprite_aggression_low   = 0.25,
        sprite_aggression_high  = 0.75,
        boss_health             = 140,
        minion_health           = 55,
        suggested_room_prefixes = ['Jungle Path', 'Ancient Temple', 'Treasure Chamber',
                                   'River Crossing', 'Village', 'Bazaar', 'Cave',
                                   'Cliff Face', 'Lost City', 'Hidden Passage'],
        suggested_object_types  = ['torch', 'map', 'rope', 'artifact', 'compass',
                                   'journal', 'key', 'gem', 'whip', 'explosives'],
        default_physics         = [PhysicsType.LOCK_KEY, PhysicsType.EXPLOSIVES,
                                   PhysicsType.CRAFTING],
        suggested_verbs_extra   = ['climb', 'dig', 'photograph', 'decipher', 'swing'],
        flavor_adjective        = 'ancient',
        flavor_noun             = 'ruins',
    ),

    WorldTheme.SITCOM: ThemeDefaults(
        theme               = WorldTheme.SITCOM,
        sd_scene_suffix     = ('sitcom set, warm interior lighting, 1960s 1970s style, '
                               'photorealistic, detailed, cozy American home, '
                               'television production quality, nostalgic'),
        sd_negative_prompt  = ('blurry, low quality, dark, scary, violent, military, '
                               'alien, medieval, cartoon, anime, text, watermark, stock photo, logo, signature, fake text, alamy, shutterstock, getty, letters, gritty'),
        base_damage             = 8,
        sprite_aggression_low   = 0.05,
        sprite_aggression_high  = 0.25,
        boss_health             = 70,
        minion_health           = 35,
        suggested_room_prefixes = ['Living Room', 'Kitchen', 'Front Stoop', 'Diner',
                                   'Office', 'Apartment', 'Backyard', 'Garage',
                                   'Neighbor\'s House', 'Town Square'],
        suggested_object_types  = ['prop', 'disguise', 'bribe_item', 'letter',
                                   'phone', 'food', 'costume', 'newspaper'],
        default_physics         = [PhysicsType.DISGUISE, PhysicsType.BRIBERY],
        suggested_verbs_extra   = ['joke', 'disguise', 'scheme', 'confess', 'bribe'],
        flavor_adjective        = 'zany',
        flavor_noun             = 'neighborhood',
    ),

    WorldTheme.CRIME_SPY: ThemeDefaults(
        theme               = WorldTheme.CRIME_SPY,
        sd_scene_suffix     = ('spy thriller, noir, cinematic, dramatic shadows, '
                               'photorealistic, detailed, atmospheric, 1960s aesthetic, '
                               'tension, suspense, professional quality'),
        sd_negative_prompt  = ('blurry, low quality, fantasy, alien, medieval, '
                               'cartoon, anime, text, watermark, stock photo, logo, signature, fake text, alamy, shutterstock, getty, letters, cheerful, colorful'),
        base_damage             = 22,
        sprite_aggression_low   = 0.3,
        sprite_aggression_high  = 0.8,
        boss_health             = 130,
        minion_health           = 60,
        suggested_room_prefixes = ['Safehouse', 'Embassy Ballroom', 'Control Room',
                                   'Vault', 'Interrogation Room', 'Rooftop',
                                   'Casino Floor', 'Underground Lab', 'Helipad'],
        suggested_object_types  = ['pistol', 'identity_papers', 'gadget', 'microfilm',
                                   'cipher', 'key', 'disguise', 'explosive', 'radio'],
        default_physics         = [PhysicsType.DISGUISE, PhysicsType.LOCK_KEY,
                                   PhysicsType.EXPLOSIVES],
        suggested_verbs_extra   = ['hack', 'decode', 'photograph', 'tail', 'interrogate'],
        flavor_adjective        = 'clandestine',
        flavor_noun             = 'operation',
    ),

    WorldTheme.DISCO: ThemeDefaults(
        theme               = WorldTheme.DISCO,
        sd_scene_suffix     = ('1970s disco club, dance floor, mirror ball, strobe lights, '
                               'neon glow, polyester fashion, fog machine, cinematic, '
                               'photorealistic, atmospheric, high energy, dramatic'),
        sd_negative_prompt  = ('blurry, low quality, daylight, outdoor, fantasy, military, '
                               'cartoon, anime, text, watermark, stock photo, logo, signature, fake text, alamy, shutterstock, getty, letters, medieval, futuristic'),
        base_damage             = 10,
        sprite_aggression_low   = 0.05,
        sprite_aggression_high  = 0.40,
        boss_health             = 90,
        minion_health           = 40,
        suggested_room_prefixes = ['Dance Floor', 'VIP Lounge', 'DJ Booth', 'Bar',
                                   'Backstage', 'Coat Check', 'Balcony', 'Hidden Room',
                                   'Entrance', 'Bathroom'],
        suggested_object_types  = ['disco_ball', 'vinyl_record', 'velvet_rope', 'champagne',
                                   'strobe_light', 'fog_machine', 'sequined_outfit', 'pass'],
        default_physics         = [],
        suggested_verbs_extra   = ['dance', 'spin', 'schmooze', 'bribe', 'sneak'],
        flavor_adjective        = 'electric',
        flavor_noun             = 'dance floor',
    ),

    WorldTheme.NIGHTCLUB: ThemeDefaults(
        theme               = WorldTheme.NIGHTCLUB,
        sd_scene_suffix     = ('upscale nightclub, ambient lighting, moody atmosphere, '
                               'cocktail lounge, neon signs, photorealistic, dramatic, '
                               'high-end interior, cinematic quality'),
        sd_negative_prompt  = ('blurry, low quality, daylight, outdoor, fantasy, military, '
                               'cartoon, anime, text, watermark, stock photo, logo, signature, fake text, alamy, shutterstock, getty, letters, medieval'),
        base_damage             = 12,
        sprite_aggression_low   = 0.1,
        sprite_aggression_high  = 0.5,
        boss_health             = 85,
        minion_health           = 40,
        suggested_room_prefixes = ['Main Bar', 'VIP Section', 'Dance Floor', 'Backstage',
                                   'Rooftop', 'Private Booth', 'Coat Check', 'Green Room',
                                   'Entrance', 'Back Office'],
        suggested_object_types  = ['cocktail', 'velvet_rope', 'id_scanner', 'guest_list',
                                   'cash_envelope', 'key_card', 'phone', 'drugs'],
        default_physics         = [],
        suggested_verbs_extra   = ['order', 'schmooze', 'bribe', 'sneak', 'photograph'],
        flavor_adjective        = 'exclusive',
        flavor_noun             = 'venue',
    ),

    WorldTheme.ORIGINAL: ThemeDefaults(
        theme               = WorldTheme.ORIGINAL,
        sd_scene_suffix     = ('detailed environment, cinematic lighting, photorealistic, '
                               'atmospheric, high quality, dramatic'),
        sd_negative_prompt  = ('blurry, low quality, distorted, ugly, cartoon, anime, '
                               'text, watermark, stock photo, logo, signature, fake text, alamy, shutterstock, getty, letters'),
        base_damage             = 15,
        sprite_aggression_low   = 0.2,
        sprite_aggression_high  = 0.6,
        boss_health             = 100,
        minion_health           = 45,
        suggested_room_prefixes = ['Entrance', 'Main Hall', 'Side Room', 'Upper Level',
                                   'Lower Level', 'Outer Area', 'Inner Chamber',
                                   'Hidden Area', 'Final Room'],
        suggested_object_types  = ['key', 'weapon', 'consumable', 'document', 'tool'],
        default_physics         = [PhysicsType.LOCK_KEY],
        suggested_verbs_extra   = [],
        flavor_adjective        = 'mysterious',
        flavor_noun             = 'place',
    ),
}


# ── Setting → SD Suffix Override Map ─────────────────────────
# Jim's refinement: "if GILLIGANS ISLAND is a SITCOM, what is the
# SETTING for the SHOW, where the ACTION takes place?"
#
# When the room namer discovers the physical setting (TROPICAL ISLAND,
# JUNKYARD, POLICE PRECINCT etc.), use it to override the genre's
# default SD scene suffix. A sitcom set in a junkyard should not
# render as "warm interior lighting, cozy American home."
#
# Keys: uppercase substrings matched against the discovered setting.
# First match wins. Falls back to theme default if no match.

SETTING_SUFFIX_MAP: List[Tuple[str, str, str]] = [
    # (setting_keyword, scene_suffix, negative_additions)

    # Tropical / Island
    ('TROPICAL',      'tropical island setting, lush jungle, palm trees, '
                      'sandy beach, ocean backdrop, warm sunlight, '
                      'photorealistic, cinematic, vivid colors, '
                      'castaway adventure, 1960s style',
                      'urban, city, indoor studio, cozy home, office'),

    ('ISLAND',        'tropical island setting, lush jungle, palm trees, '
                      'sandy beach, ocean backdrop, warm sunlight, '
                      'photorealistic, cinematic, vivid colors, '
                      'castaway adventure, 1960s style',
                      'urban, city, indoor studio, cozy home, office'),

    # Junkyard / Salvage
    ('JUNKYARD',      'urban junkyard, piled salvage and scrap metal, '
                      'rusty cars and appliances, gritty 1970s Los Angeles, '
                      'photorealistic, cinematic, warm afternoon light, '
                      'cluttered outdoor yard, nostalgic',
                      'clean, sterile, suburban, forest, ocean'),

    ('SALVAGE',       'urban junkyard, piled salvage and scrap metal, '
                      'rusty cars and appliances, gritty 1970s Los Angeles, '
                      'photorealistic, cinematic, warm afternoon light',
                      'clean, sterile, suburban, forest, ocean'),

    # Police / Precinct
    ('POLICE',        'police precinct interior, 1970s detective squad room, '
                      'metal desks, fluorescent lighting, wanted posters, '
                      'photorealistic, cinematic, gritty urban atmosphere, '
                      'television production quality, nostalgic',
                      'outdoor, tropical, fantasy, suburban home'),

    ('PRECINCT',      'police precinct interior, 1970s detective squad room, '
                      'metal desks, fluorescent lighting, wanted posters, '
                      'photorealistic, cinematic, gritty urban atmosphere',
                      'outdoor, tropical, fantasy, suburban home'),

    # Farm / Rural
    ('FARM',          'rural farm setting, green fields, wooden barn, '
                      '1960s American countryside, photorealistic, '
                      'warm natural light, pastoral atmosphere, nostalgic',
                      'urban, city, tropical, ocean'),

    # Military / War / Field Hospital
    ('MILITARY',      'military field hospital, olive drab tents, '
                      'Korean war era, photorealistic, cinematic, '
                      'dramatic shadows, wartime atmosphere',
                      'clean, suburban, tropical, cheerful'),

    ('HOSPITAL',      'military field hospital, olive drab tents, '
                      'surgical equipment, Korean war era, photorealistic, '
                      'cinematic, dramatic shadows, wartime atmosphere',
                      'clean, suburban, tropical, cheerful'),

    # Cruise Ship
    ('CRUISE',        'luxury cruise ship interior, 1970s ocean liner, '
                      'wood paneling, porthole windows, nautical decor, '
                      'photorealistic, cinematic, warm lighting',
                      'outdoor jungle, urban, military'),

    ('SHIP',          'ship deck and interior, nautical setting, '
                      'ocean horizon, ropes and rigging, '
                      'photorealistic, cinematic, warm lighting',
                      'urban, city, suburban'),

    # Space / Sci-Fi
    ('SPACE',         'space station interior, zero gravity, stars through '
                      'portholes, futuristic technology, photorealistic, '
                      'cinematic, dramatic lighting, sci-fi atmosphere',
                      'outdoor, tropical, medieval, suburban'),

    # Superhero HQ
    ('HALL OF',       'superhero headquarters interior, Hall of Justice, '
                      'bold primary colors, heroic architecture, '
                      'computer consoles and screens, dramatic upward lighting, '
                      '1970s animated superhero aesthetic, photorealistic, cinematic',
                      'dark, gritty, medieval, suburban, tropical'),

    ('JUSTICE',       'superhero headquarters interior, Hall of Justice, '
                      'bold primary colors, heroic architecture, '
                      'computer consoles and screens, dramatic upward lighting, '
                      '1970s animated superhero aesthetic, photorealistic, cinematic',
                      'dark, gritty, medieval, suburban, tropical'),

    ('SUPERHERO',     'superhero headquarters, bold heroic architecture, '
                      'dramatic lighting, primary colors, '
                      'photorealistic, cinematic, high energy atmosphere',
                      'dark, gritty, medieval, suburban, tropical'),

    ('BATCAVE',       'bat cave interior, stalactites, dramatic spotlights, '
                      'sleek Batmobile visible, dark stone walls, '
                      'photorealistic, cinematic, dramatic shadows, '
                      'gothic heroic atmosphere',
                      'bright, cheerful, tropical, suburban'),

    # Haunted / Horror
    ('HAUNTED',       'haunted Victorian mansion, dark corridors, '
                      'cobwebs, candlelight, gothic atmosphere, '
                      'photorealistic, cinematic, dramatic shadows',
                      'cheerful, bright, tropical, outdoor'),

    # Prison / POW Camp
    ('PRISON',        'prisoner of war camp, World War II barracks, '
                      'barbed wire, guard towers, wooden bunks, '
                      'photorealistic, cinematic, atmospheric, '
                      'dramatic shadows, wartime',
                      'tropical, cheerful, suburban'),

    # Western / Frontier
    ('WESTERN',       'American Old West frontier town, dusty main street, '
                      'wooden saloon, hitching posts, desert landscape, '
                      '1870s frontier atmosphere, photorealistic, cinematic, '
                      'warm golden sunlight, nostalgic western',
                      'urban, modern, tropical, sci-fi, indoor studio'),

    ('FRONTIER',      'American Old West frontier town, dusty main street, '
                      'wooden saloon, hitching posts, desert landscape, '
                      '1870s frontier atmosphere, photorealistic, cinematic, '
                      'warm golden sunlight, nostalgic western',
                      'urban, modern, tropical, sci-fi, indoor studio'),

    ('ARIZONA',       'Arizona Territory frontier, red rock desert, '
                      'wooden frontier buildings, dusty trails, '
                      'sagebrush and cacti, 1870s American West, '
                      'photorealistic, cinematic, warm desert light',
                      'urban, modern, tropical, sci-fi, lush green'),

    ('TERRITORY',     'American frontier territory, dusty plains, '
                      'wooden frontier buildings, open rangeland, '
                      '1870s Old West, photorealistic, cinematic, '
                      'warm golden light, vast sky',
                      'urban, modern, tropical, sci-fi'),

    ('SALOON',        'frontier saloon interior, wooden bar, '
                      'oil lamps, card tables, wanted posters on wall, '
                      '1870s American West, photorealistic, cinematic, '
                      'warm amber lighting, dusty floorboards',
                      'modern, urban, tropical, sci-fi'),

    ('PRISONER',      'prisoner of war camp, World War II barracks, '
                      'barbed wire, guard towers, wooden bunks, '
                      'photorealistic, cinematic, atmospheric',
                      'tropical, cheerful, suburban'),
]


def get_setting_suffix(setting: str, theme_suffix: str,
                       theme_negative: str) -> Tuple[str, str]:
    """
    Given the physical setting discovered by the room namer,
    return (scene_suffix, negative_prompt) — either a setting-specific
    override or the theme default if no match.

    Usage in create_world.py:
        scene_suffix, negative = get_setting_suffix(
            _room_namer.last_setting,
            theme_defaults.sd_scene_suffix,
            theme_defaults.sd_negative_prompt,
        )
    """
    if not setting:
        return theme_suffix, theme_negative

    setting_upper = setting.upper()
    for keyword, suffix, neg_additions in SETTING_SUFFIX_MAP:
        if keyword in setting_upper:
            # Strip terms from the theme negative that now appear in the
            # positive suffix — e.g. SCIFI theme has "futuristic, sci-fi"
            # in its negative, but the SPACE suffix wants them as positives.
            suffix_words = {w.strip().lower()
                            for w in suffix.replace(',', ' ').split()
                            if len(w.strip()) > 3}
            neg_parts = [t.strip() for t in theme_negative.split(',')
                         if t.strip()]
            cleaned_neg_parts = [
                t for t in neg_parts
                if not any(sw in t.lower() for sw in suffix_words)
            ]
            combined_neg = ', '.join(cleaned_neg_parts)
            if neg_additions:
                combined_neg = combined_neg.rstrip(', ') + ', ' + neg_additions
            return suffix, combined_neg

    # No setting match — use theme default
    return theme_suffix, theme_negative


# ── Theme Classifier ─────────────────────────────────────────

class ThemeEngine:
    """
    Classifies a world name into a theme and returns complete defaults.
    This is a pure function wrapped in a class for testability.
    """

    def classify(self, world_name: str) -> WorldTheme:
        import re
        name_lower = world_name.lower().strip()
        scores: Dict[WorldTheme, int] = {t: 0 for t in WorldTheme}

        for theme, keywords in THEME_KEYWORDS:
            for kw in keywords:
                # Word-boundary match — 'bar' must not fire inside 'barney' or 'barracks'
                pattern = r'(?<![a-z0-9])' + re.escape(kw) + r'(?![a-z0-9])'
                if re.search(pattern, name_lower):
                    scores[theme] += (2 if len(kw) > 6 else 1)

        best_theme = max(scores, key=lambda t: scores[t])
        if scores[best_theme] == 0:
            return WorldTheme.ORIGINAL
        return best_theme

    def get_defaults(self, world_name: str) -> ThemeDefaults:
        theme = self.classify(world_name)
        return THEME_DEFAULTS[theme]

    def get_defaults_for_theme(self, theme: WorldTheme) -> ThemeDefaults:
        return THEME_DEFAULTS[theme]

    def all_themes(self) -> List[WorldTheme]:
        return list(WorldTheme)

    def theme_display_name(self, theme: WorldTheme) -> str:
        names = {
            WorldTheme.SCIFI:      '🛸 Sci-Fi / Space',
            WorldTheme.MILITARY:   '🎖️  Military / War',
            WorldTheme.FANTASY:    '⚔️  Fantasy / Magic',
            WorldTheme.DOMESTIC:   '🏠 Domestic / Cozy',
            WorldTheme.HORROR:     '👻 Horror / Mystery',
            WorldTheme.ADVENTURE:  '🗺️  Adventure / Exploration',
            WorldTheme.SITCOM:     '📺 Sitcom / Comedy',
            WorldTheme.CRIME_SPY:  '🕵️  Crime / Spy',
            WorldTheme.ORIGINAL:   '✨ Original',
        }
        return names.get(theme, theme.value)
