# Referências e licenças

## ZeldaWWHDRecomp

- Fonte: https://github.com/ZeldaWWHDRecomp/ZeldaWWHDRecomp
- Commit de referência: `defb89f21607345e2e97b2c145a071a3f362640c`.
- Licença: Mozilla Public License 2.0.
- O arquivo `patches/recompiler-hook-paths.patch` modifica `tools/recomp/recomp.py` para aceitar uma lista explícita de hooks. Mantém o padrão original quando o argumento é omitido.
- O checkout `upstream/` é obtido separadamente. Seus arquivos, licenças e créditos de terceiros permanecem nesse checkout. Não estão incorporados no histórico deste repositório.
- O projeto Android de ZeldaWWHDRecomp inclui contribuições de rhemfur, que também é o proprietário deste projeto.

## cdecrypt

- Fonte: https://github.com/VitaSmith/cdecrypt
- Commit usado na extração local inicial: `0ca58c66b0f23309c69b691caf6d39bf8868d96d`.
- Ferramenta de extração obtida e compilada separadamente. Nenhum código ou binário de cdecrypt está incluído neste repositório.
- Consulte a licença e os créditos no projeto original antes de redistribuir essa ferramenta.

## cttt-decomp

- Fonte: https://github.com/shibbo/cttt-decomp
- Referência de pesquisa da versão Switch. Não foi incorporado código desse projeto neste protótipo.

## Componentes adaptados no runtime de diagnóstico

- `runtime/filesystem.cpp` adapta `runtime/src/hle/fs.cpp` de ZeldaWWHDRecomp (MPL-2.0), removendo os redirecionamentos de mods/idiomas de Zelda e restringindo caminhos/escritas.
- `runtime/coreinit_boot.cpp` adapta as consultas de debugger e clocks de `coreinit_misc.cpp` da mesma base.
- `patches/strict-diagnostic-hle.patch` modifica `runtime/src/core.cpp` exclusivamente quando `CT_DIAGNOSTIC_STRICT_HLE` está ativo.
- Os layouts e comportamentos de fast mutex, MCP e UC foram consultados na fonte de Cemu, MPL-2.0: https://github.com/cemu-project/Cemu/blob/main/src/Cafe/OS/libs/coreinit/coreinit_Thread.h , https://github.com/cemu-project/Cemu/blob/main/src/Cafe/OS/libs/coreinit/coreinit_Synchronization.cpp , https://github.com/cemu-project/Cemu/blob/main/src/Cafe/OS/libs/coreinit/coreinit_MCP.h e coreinit_MCP.cpp.
- Nenhum código da versão Switch nem assets Nintendo foi adicionado.
