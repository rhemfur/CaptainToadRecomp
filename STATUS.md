# Captain Toad Android: primeiro marco

Trabalho realizado em 10/10/2026, em `C:\DEV\Captain Toad`.

**Resultado: executável EU com update v16 traduzido para C e compilado para Android ARM64. Ainda não há um jogo executável nem APK.**

## Concluído

- Base pública ZeldaWWHDRecomp clonada no diretório autorizado, sem modificar o projeto Zelda já existente.
- Pacotes de Captain Toad extraídos separadamente para `work/extracted/base` e `work/extracted/update`, preservando os originais em Downloads.
- Cópia atualizada criada em `game/`: 1.572 arquivos; 124 caminhos da base substituídos pelo update. Todos os hashes das cópias foram verificados contra a respectiva origem extraída.
- Executável identificado: `Kinopio.rpx`, SHA-256 `3e867817ff4cfbefcd1f3323fe1e97919852cd86aee3738bd8d44e6e460a0464`.
- Perfil `CT-EUR-v16` criado com identidade de endereços e zero hooks de Zelda.
- Geradas 45.773 funções, em 48 unidades C.
- Compilação concluída com NDK 30.0.16248370 / Clang 21, ABI arm64-v8a e Android API 33.
- Objetos ELF64/AArch64 verificados; produzida `build/android-gamecode/libcaptain_toad_gamecode.a` (447.912.254 bytes).
- Passaram os 17 testes existentes de identificação e mapeamento de builds do recompilador.
- Repositório local iniciado; jogo, código gerado, builds e relatórios locais excluídos pelo `.gitignore`. O primeiro marco foi validado localmente; a publicação do projeto contém apenas ferramentas, metadados e documentação.

SHA-256 da biblioteca estática local: `457f4f386460d4250950b5a8d496fd22d0c14935c43d601a910274e81c52b30a`.

## Auditoria inicial

Encontrados 370 imports: 362 funções e 8 objetos de dados. A busca lexical encontrou definições diretas no runtime para 300 funções. Os 62 imports abaixo ainda exigem análise de implementação/aliases:

| Biblioteca | Funções sem definição direta encontrada |
|---|---:|
| gx2 | 16 |
| coreinit | 11 |
| nn_nfp (amiibo) | 10 |
| mic | 8 |
| snd_user | 7 |
| padscore | 4 |
| snd_core | 3 |
| nn_save | 3 |

Presença de uma definição não comprova comportamento correto ou disponibilidade na ligação Android. Ausência nesta busca não exclui definições geradas por macros. Os 8 imports de dados precisam de uma auditoria específica do loader.

O tradutor sinalizou 36 palavras com opcode principal 0 e duas chamadas a símbolos indefinidos. Continuam gerando diagnósticos explícitos; não foram substituídos por funções vazias. É necessário investigar se as palavras são padding/dados internos ou caminhos executáveis.

## Próximo marco

Adaptar o loader e a composição do runtime para Captain Toad, retirar as dependências de hooks e recursos de Zelda, resolver as APIs necessárias para boot e obter menu/primeira fase. Depois integrar o aplicativo Android e validar controles, áudio, save e pausa/retomada em aparelho real.

A biblioteca estática contém código gerado compilado e ainda pode referenciar símbolos externos: a ligação do runtime e a execução permanecem por fazer. Compilação bem-sucedida não comprova compatibilidade ou correção do jogo.

## Arquivos principais no diretório de trabalho

- `README.md`: estado atual e comandos reproduzíveis.
- `CMakeLists.txt`: alvo de biblioteca estática Android.
- `profiles/captain-toad-eur-v16.json`: perfil do RPX identificado.
- `tools/prepare_game.py`: criação e verificação da árvore atualizada.
- `tools/audit_rpx.py`: inventário de seções, relocations e imports.
- `tools/recompile.py`: geração sem hooks de Zelda e com conferência do SHA-256.
- `tools/build_android.ps1`: compilação usando o SDK/NDK instalado.
- `patches/recompiler-hook-paths.patch`: extensão pequena e reproduzível no recompilador de referência.
- `local-reports/game-manifest.json` e `local-reports/rpx-audit.json`: resultados detalhados locais.

Referências preservadas: ZeldaWWHDRecomp `defb89f21607345e2e97b2c145a071a3f362640c`; cdecrypt `0ca58c66b0f23309c69b691caf6d39bf8868d96d`.

## Marco de diagnóstico de boot — 10/10/2026

O código recompilado entrou no boot no Galaxy S25 Ultra e no Windows. As primeiras dependências foram resolvidas com serviços de debugger/clocks, OSFastMutex, filesystem e MCP/UC. O boot atual chega a `gx2.GX2Init`; ainda não há imagem ou APK jogável.

No S25 Ultra, criação de instância Vulkan 1.3 e dispositivo lógico foi verificada, com Adreno 830 reportando API 1.3.284. Passaram testes de SHA-256, concorrência/recursão de mutex, arquivos/saves sintéticos e registros MCP/UC. Cinco testes CTest também passaram no Windows; os 17 testes existentes do recompilador passaram. Logs e binários são locais e não foram publicados.

Próximo trabalho: integrar GX2 e o renderer Vulkan para chegar à primeira imagem. Consultar README para os comandos reproduzíveis e limitações atuais.
