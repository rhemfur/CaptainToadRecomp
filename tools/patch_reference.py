"""Add an explicit hook-list argument while preserving the reference recompiler defaults."""
from pathlib import Path
import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('upstream', type=Path)
args = parser.parse_args()
path = args.upstream / 'tools/recomp/recomp.py'
source = path.read_text(encoding='utf-8')
if 'hook_paths=None' in source:
    print('reference extension already present')
else:
    old_signature = 'def __init__(self, path, build=None, mod_hooks=False):'
    old_hooks = 'game_builds.read_hooks(game_builds.hook_files(), self.build)'
    if source.count(old_signature) != 1 or source.count(old_hooks) != 1:
        raise SystemExit('reference changed: patch needs review')
    source = source.replace(old_signature, 'def __init__(self, path, build=None, mod_hooks=False, hook_paths=None):')
    source = source.replace(old_hooks, 'game_builds.read_hooks(\n            game_builds.hook_files() if hook_paths is None else hook_paths, self.build)')
    path.write_text(source, encoding='utf-8', newline='\n')
    print('reference extension applied; defaults unchanged; [] explicitly disables all hooks')
