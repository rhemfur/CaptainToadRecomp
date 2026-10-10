"""Make missing HLE functions terminate only the Captain Toad diagnostic build."""
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('upstream', type=Path)
args = parser.parse_args()
path = args.upstream / 'runtime/src/core.cpp'
source = path.read_text(encoding='utf-8')
signature = 'extern "C" void hle_unimplemented(Cpu* c, const char* lib, const char* name) {'
if '#ifdef CT_DIAGNOSTIC_STRICT_HLE' in source:
    print('strict diagnostic extension already present')
elif source.count(signature) != 1:
    raise SystemExit('reference changed: strict diagnostic patch needs review')
else:
    extension = '''
#ifdef CT_DIAGNOSTIC_STRICT_HLE
    log_msg("[ct-stop] missing HLE %s.%s r3=%08X r4=%08X r5=%08X lr=%08X", lib, name,
            c->r[3], c->r[4], c->r[5], c->lr);
    std::_Exit(78);
#endif
'''
    path.write_text(source.replace(signature,signature + extension),encoding='utf-8',newline='\n')
    print('strict diagnostic extension applied; normal runtime behavior unchanged')
