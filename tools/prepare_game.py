"""Merge locally extracted Wii U base/update files without modifying either source."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def metadata(directory):
    root = ET.parse(directory / 'code/app.xml').getroot()
    return {'title_id': root.findtext('title_id').strip().lower(),
            'title_version': int(root.findtext('title_version'), 16)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--update', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    base, update, output = [p.resolve() for p in (args.base, args.update, args.output)]
    for source in (base, update):
        if output == source or output.is_relative_to(source) or source.is_relative_to(output):
            parser.error('output and inputs must be separate directory trees')
    if output.exists() and any(output.iterdir()):
        parser.error('output must be empty; use a new directory to preserve prior runs')
    bm, um = metadata(base), metadata(update)
    if bm['title_id'] != '0005000010180700' or um['title_id'] != '0005000e10180700':
        parser.error('expected Captain Toad EUR base and its matching EUR update')
    if um['title_version'] != 16:
        parser.error('this initial profile supports update version 16 only')
    chosen = {}
    base_count = update_count = overrides = 0
    for label, source in [('base', base), ('update', update)]:
        for file in sorted(source.rglob('*')):
            if not file.is_file():
                continue
            relative = file.relative_to(source)
            if relative.parts[0] not in ('code', 'content', 'meta'):
                continue
            if file.is_symlink():
                parser.error('symlinked source files are not accepted')
            key = relative.as_posix().casefold()
            if key in chosen and chosen[key][0] == label:
                parser.error('case-insensitive path collision: ' + str(relative))
            if label == 'base':
                base_count += 1
            else:
                update_count += 1
                overrides += key in chosen
            # Preserve the base spelling for paths overridden by the update.
            destination = chosen[key][2] if key in chosen else relative
            chosen[key] = (label, file, destination)
    if 'code/kinopio.rpx' not in chosen:
        parser.error('Kinopio.rpx is missing')
    records = []
    for label, source, relative in sorted(chosen.values(), key=lambda x: str(x[2]).casefold()):
        dest = output / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        sha = digest(source)
        if digest(dest) != sha:
            raise RuntimeError('copy verification failed: ' + str(relative))
        records.append({'path': relative.as_posix(), 'source': label,
                        'bytes': dest.stat().st_size, 'sha256': sha})
    manifest = {'base': bm, 'update': um, 'base_files': base_count,
                'update_files': update_count, 'overridden_files': overrides,
                'effective_files': len(records), 'copy_hashes_verified': True, 'files': records}
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in manifest.items() if k != 'files'}, indent=2))


if __name__ == '__main__':
    main()
