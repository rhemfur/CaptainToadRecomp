"""Inspect a local RPX and compare imports with source definitions in the reference runtime."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import struct
import sys


def source_exports(upstream):
    definitions = collections.defaultdict(list)
    for path in sorted((upstream / 'runtime/src').rglob('*')):
        if path.suffix not in ('.cpp', '.c', '.mm', '.h'):
            continue
        source = path.read_text(encoding='utf-8', errors='replace')
        # This is a source inventory, not linker validation or proof of behavior.
        source = re.sub(r'/\*.*?\*/|//[^\n]*', '', source, flags=re.S)
        for match in re.finditer(r'\bHLE\(\s*(\w+)\s*,\s*(\w+)\s*\)\s*\{', source):
            symbol = 'imp_' + match[1] + '_' + match[2]
            definitions[symbol].append(path.relative_to(upstream).as_posix())
        for match in re.finditer(r'\b(?:void|uint32_t|int)\s+(imp_\w+)\s*\([^;{}]*\)\s*\{', source):
            definitions[match[1]].append(path.relative_to(upstream).as_posix())
    return definitions


def inspect(rpx_path, upstream):
    sys.path[:0] = [str(upstream / 'tools/recomp'), str(upstream / 'tools')]
    from analyze import Program
    from recomp import c_ident
    program = Program(str(rpx_path))
    program.discover()
    definitions = source_exports(upstream)
    imports = []
    seen = set()
    libraries = collections.Counter()
    for symbol in program.rpx.symbols:
        if not symbol.import_lib or symbol.type == 3:
            continue
        identity = (symbol.import_lib, symbol.name, symbol.import_kind, symbol.value)
        if identity in seen:
            continue
        seen.add(identity)
        host = 'imp_' + c_ident(symbol.import_lib.replace('.rpl', '')) + '_' + c_ident(symbol.name)
        matches = definitions.get(host, []) if symbol.import_kind == 'f' else []
        imports.append({'library': symbol.import_lib, 'name': symbol.name,
                        'kind': symbol.import_kind, 'slot': f'{symbol.value:08x}',
                        'host_symbol': host, 'source_definitions': matches,
                        'status': 'source_definition_found' if matches else
                                  'data_import_needs_loader_audit' if symbol.import_kind == 'd' else
                                  'no_direct_source_definition_found'})
        libraries[symbol.import_lib] += 1
    raw = rpx_path.read_bytes()
    sections = [{'name': s.name, 'type': s.type, 'flags': f'{s.flags:08x}',
                 'address': f'{s.addr:08x}', 'bytes': s.size} for s in program.rpx.sections]
    return {'file': rpx_path.name, 'sha256': hashlib.sha256(raw).hexdigest(),
            'elf_machine': struct.unpack_from('>H', raw, 18)[0],
            'entry_point': f'{program.entry:08x}', 'file_bytes': len(raw),
            'text_bytes': program.text.size, 'discovered_function_entries': len(program.entries),
            'jump_tables': len(program.jump_tables), 'relocations': len(program.rpx.relocs),
            'import_call_sites': len(program.import_calls),
            'undefined_call_sites': len(program.undef_calls),
            'libraries': dict(sorted(libraries.items())),
            'import_status_counts': dict(collections.Counter(x['status'] for x in imports)),
            'sections': sections, 'imports': imports,
            'limitations': ['Source matching does not prove API correctness or availability in a target build.',
                            'Macro-generated aliases may be absent from this lexical inventory.',
                            'Static function discovery requires runtime validation.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reports = [inspect(path, args.upstream.resolve()) for path in sorted((args.game / 'code').iterdir())
               if path.suffix.lower() in ('.rpx', '.rpl')]
    if not reports:
        parser.error('no executable found in game/code')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reports, indent=2) + '\n', encoding='utf-8')
    for report in reports:
        print(json.dumps({k: v for k, v in report.items() if k not in ('sections', 'imports')}, indent=2))


if __name__ == '__main__':
    main()
