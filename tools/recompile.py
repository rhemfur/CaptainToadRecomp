"""Translate the identified Captain Toad executable with an identity address map and no Zelda hooks."""
import argparse
import inspect
import json
from pathlib import Path
import sys


def main():
    root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', type=Path, default=root / 'upstream')
    parser.add_argument('--game', type=Path, default=root / 'game')
    parser.add_argument('--profile', type=Path, default=root / 'profiles/captain-toad-eur-v16.json')
    parser.add_argument('--output', type=Path, default=root / 'build/gen')
    args = parser.parse_args()
    sys.path[:0] = [str(args.upstream / 'tools/recomp'), str(args.upstream / 'tools')]
    import builds
    from rpx import Rpx
    from recomp import Recompiler
    profile = json.loads(args.profile.read_text(encoding='utf-8'))
    rpx_path = args.game / 'code' / profile['rpx']
    if builds.file_sha256(rpx_path) != profile['rpx_sha256']:
        parser.error('RPX SHA-256 does not match the independently identified EUR v16 profile')
    if profile['hooks']:
        parser.error('this prototype intentionally requires an empty hook list')
    if 'hook_paths' not in inspect.signature(Recompiler.__init__).parameters:
        parser.error('reference recompiler is missing the explicit hook_paths extension')
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('output must be empty; use a new --output for another generation')
    rpx = Rpx(str(rpx_path))
    text = rpx.by_name['.text']
    data = [rpx.by_name[name] for name in ('.rodata', '.data', '.bss') if name in rpx.by_name]
    identity = builds.Build({'name': profile['name'], 'title_id': profile['title_id'],
                             'rpx_sha256': profile['rpx_sha256'],
                             'code_bounds': [f'{text.addr:08x}', f'{text.addr + text.size:08x}'],
                             'data_bounds': [f'{min(s.addr for s in data):08x}',
                                             f'{max(s.addr + s.size for s in data):08x}'],
                             'code_steps': [], 'data_steps': []})
    compiler = Recompiler(str(rpx_path), identity, mod_hooks=False, hook_paths=[])
    compiler.run(str(args.output), 30000)
    summary = {'profile': profile, 'generated_functions': len(compiler.sorted_entries),
               'zelda_hooks': len(compiler.hooks), 'instruction_hooks': len(compiler.sites),
               'unhandled_instructions': dict(compiler.unhandled),
               'used_imports': len(compiler.used_imports),
               'warning': 'Translation and compilation do not establish executable correctness or game compatibility.'}
    (args.output / 'captain-toad-generation.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
