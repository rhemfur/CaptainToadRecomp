"""Add an explicit hook-list argument while preserving the reference recompiler defaults."""
from pathlib import Path
import argparse
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('upstream', type=Path)
args = parser.parse_args()
path = args.upstream / 'tools/recomp/recomp.py'
source = path.read_text(encoding='utf-8')
if 'hook_paths=None' in source:
    print('reference extension already present')
else:
    # The signature gained preserve_registers in later references; hook_paths goes last either way.
    signature = re.compile(r'def __init__\(self, path, build=None, mod_hooks=False, decomp_hooks=None'
                           r'(, preserve_registers=False)?\):')
    old_hooks = 'game_builds.read_hooks(game_builds.hook_files(), self.build)'  # defb89f, d23522e
    old_list = '        hook_list = game_builds.hook_files()\n'                  # later references
    if len(signature.findall(source)) != 1 or source.count(old_hooks) + source.count(old_list) != 1:
        raise SystemExit('reference changed: patch needs review')
    source = signature.sub(lambda m: m.group(0)[:-2] + ', hook_paths=None):', source)
    source = source.replace(old_hooks, 'game_builds.read_hooks(\n            game_builds.hook_files() if hook_paths is None else hook_paths, self.build)')
    source = source.replace(old_list, '        hook_list = game_builds.hook_files() if hook_paths is None else list(hook_paths)\n')
    path.write_text(source, encoding='utf-8', newline='\n')
    print('reference extension applied; defaults unchanged; [] explicitly disables all hooks')
