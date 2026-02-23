"""
N2NHU World Generator - Entry Point
Run as:  python __main__.py [options]
         python __main__.py --gui
         python __main__.py --name "Barbie World" --chars "Barbie,Ken,Skipper" --rooms 12

N2NHU Labs for Applied Artificial Intelligence
"""

import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(
        prog='N2NHU World Generator',
        description='N2NHU World Generator — Zero-Invalid INI World Compiler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  python __main__.py --name "Barbie World" --chars "Barbie,Ken,Skipper"
  python __main__.py --name "Area 51" --rooms 35 --physics energy,teleportation,alien_tech
  python __main__.py --name "MASH 4077" --rooms 19 --physics medical,disguise,bribery
  python __main__.py --name "Zork" --rooms 30 --physics magic,lock_key,crafting
  python __main__.py --gui    (launch 7-step wizard)

PHYSICS CHOICES:
  temperature, energy, lock_key, crafting, teleportation,
  disguise, explosives, bribery, magic, medical, growth, alien_tech
        """
    )
    parser.add_argument('--name',    default='My World',
                        help='World name (drives theme classification)')
    parser.add_argument('--chars',   default='',
                        help='Comma-separated character names')
    parser.add_argument('--rooms',   type=int, default=20,
                        help='Number of rooms (3-100, default 20)')
    parser.add_argument('--physics', default='',
                        help='Comma-separated physics types')
    parser.add_argument('--output',  default='./generated_world',
                        help='Output directory for INI files')
    parser.add_argument('--sd-host', default='127.0.0.1')
    parser.add_argument('--sd-port', type=int, default=7860)
    parser.add_argument('--gui',     action='store_true',
                        help='Launch the wizard GUI')

    args = parser.parse_args()

    if args.gui or len(sys.argv) == 1:
        from wizard import run_gui
        run_gui()
        return

    from world_model import PhysicsType
    from generator import WorldGenerator, GeneratorRequest

    physics_map = {p.value: p for p in PhysicsType}
    physics_types = []
    if args.physics:
        for p in args.physics.split(','):
            p = p.strip()
            if p in physics_map:
                physics_types.append(physics_map[p])
            else:
                print(f"WARNING: Unknown physics type '{p}' — skipping")
                print(f"  Valid: {', '.join(physics_map.keys())}")

    chars = [c.strip() for c in args.chars.split(',') if c.strip()] if args.chars else []

    request = GeneratorRequest(
        world_name      = args.name,
        character_names = chars,
        room_count      = args.rooms,
        physics_types   = physics_types,
        output_dir      = args.output,
        sd_host         = args.sd_host,
        sd_port         = args.sd_port,
    )

    print(f"\nN2NHU World Generator  v1.0")
    print(f"N2NHU Labs for Applied Artificial Intelligence")
    print(f"{'='*55}")
    print(f"World:      {request.world_name}")
    print(f"Characters: {', '.join(request.character_names) or '(none)'}")
    print(f"Rooms:      {request.room_count}")
    print(f"Physics:    {[p.value for p in request.physics_types] or '(theme defaults)'}")
    print(f"Output:     {request.output_dir}")
    print()

    gen = WorldGenerator()
    preview = gen.preview(request)
    print(f"Theme: {preview['theme_display']}")
    print(f"SD:    {preview['sd_suffix'][:70]}...")
    print()
    print("Generating...")

    result = gen.generate(request)
    print()
    print(result.display_summary())

    if result.success:
        print(f"\nFILES WRITTEN:")
        for name, path in result.written_files.items():
            print(f"  OK  {os.path.basename(path)}")
        print(f"\nCopy these 6 files to your game engine config/ folder.")
        print(f"Launch ZORK_RPG_Server.exe. Your world is ready.\n")
        sys.exit(0)
    else:
        print(f"\nERRORS:")
        for err in result.validation_errors:
            print(f"  {err}")
        sys.exit(1)

if __name__ == '__main__':
    main()
