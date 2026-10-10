# Captain Toad EUR — protótipo de recompilação para Android

Projeto iniciado em `C:\DEV\Captain Toad` em 10/10/2026. O alvo inicial é a edição Wii U EUR com update interno v16. O executável já foi traduzido, compilado e entrou no boot em diagnóstico nativo no Windows e no Galaxy S25 Ultra. O boot atualmente para em GX2Init: ainda não há imagem, menu, jogabilidade ou APK.

## Preparar uma nova cópia do projeto

Requisitos: Git, Python 3.10 ou mais recente e, para compilar ARM64, Android SDK com NDK/CMake/Ninja. O protótipo foi validado no Windows com Python 3.11.

```powershell
git clone https://github.com/rhemfur/CaptainToadRecomp.git
cd CaptainToadRecomp
powershell -ExecutionPolicy Bypass -File tools/setup_reference.ps1
```

O script baixa o commit fixado do runtime/recompilador e aplica a extensão de hooks. Ele preserva um checkout existente e recusa alterar uma versão diferente automaticamente.

Forneça suas próprias cópias de Captain Toad Wii U EUR e update v16, extraídas separadamente com as pastas `code/content/meta`. Um extrator compatível com pacotes NUS é o [cdecrypt](https://github.com/VitaSmith/cdecrypt). As ferramentas deste repositório não incluem jogo, tickets, chaves ou o extrator.

Depois de colocar as duas árvores em `work/extracted/base` e `work/extracted/update`:

```powershell
python tools/prepare_game.py --base work/extracted/base --update work/extracted/update --output game --manifest local-reports/game-manifest.json
python tools/audit_rpx.py --game game --upstream upstream --output local-reports/rpx-audit.json
python tools/recompile.py
powershell -ExecutionPolicy Bypass -File tools/build_android.ps1
```

Os diretórios de saída da preparação e da geração devem estar vazios. Os comandos geram uma biblioteca estática e um executável de diagnóstico sem interface gráfica. Eles ainda não geram APK ou jogo jogável.

## Estrutura

- `tools/`: preparação da cópia atualizada, auditoria do RPX, geração de C e build ARM64.
- `profiles/captain-toad-eur-v16.json`: identificação por SHA-256 do RPX atualizado, sem hooks de Zelda.
- `upstream/`: checkout local de ZeldaWWHDRecomp, mantido como referência e ignorado no repositório deste projeto.
- `work/extracted/base` e `work/extracted/update`: extrações separadas dos pacotes originais.
- `game/`: cópia efetiva, com os arquivos do update sobre os caminhos correspondentes da base.
- `local-reports/`: manifesto de cópia e auditoria detalhada dos imports.
- `build/gen/`: C gerado localmente do jogo.
- `runtime/`: diagnóstico, APIs de startup, fast mutex, filesystem e testes.
- `build/android-gamecode/`: biblioteca estática ARM64 e executável `ct-diagnostic`.

Os arquivos de jogo, tickets, chaves, código derivado do jogo e builds são ignorados pelo Git. Permanecem na máquina. Um APK futuro que incorpore esse código gerado exige o mesmo cuidado de distribuição da base original.

## Referências fixadas

- ZeldaWWHDRecomp: `defb89f21607345e2e97b2c145a071a3f362640c`, https://github.com/ZeldaWWHDRecomp/ZeldaWWHDRecomp . Licença MPL-2.0 preservada no checkout.
- Extrator cdecrypt: `0ca58c66b0f23309c69b691caf6d39bf8868d96d`, https://github.com/VitaSmith/cdecrypt . Compilado localmente em `work/cdecrypt`, com a licença original preservada.

O checkout Zelda recebeu uma extensão pequena em `tools/recomp/recomp.py`: o argumento opcional `hook_paths` mantém o comportamento original quando omitido e permite passar `[]` explicitamente. Esse protótipo sempre usa `[]`; nenhum endereço/hook específico de Zelda é aplicado a Captain Toad. `tools/patch_reference.py` reproduz essa alteração e recusa um formato de fonte inesperado.

## Estado identificado

- Executável: `Kinopio.rpx`, versão atualizada, SHA-256 `3e867817ff4cfbefcd1f3323fe1e97919852cd86aee3738bd8d44e6e460a0464`.
- Entry point: `0x02511BB0`.
- Texto descomprimido: 5.746.620 bytes.
- Código gerado: 45.773 funções em 48 unidades C; zero hooks de jogo e zero hooks de instrução.
- Imports: 362 funções e 8 objetos de dados, distribuídos por 12 bibliotecas.
- A auditoria lexical encontrou definições diretas para 300 funções e não encontrou para 62. Isso não confirma correção nem ligação final: macros, aliases e condições de compilação precisam de verificação.
- Tradução sinalizou 36 palavras com opcode principal 0. Os pontos continuam chamando `ppc_unimplemented`; não foram alterados para NOP. É necessário determinar se são dados/padding ou caminhos executáveis.
- A análise encontrou duas chamadas a símbolo indefinido, que também permanecem diagnósticos explícitos.

Boot de diagnóstico confirmado no Android e no Windows, até a chamada GX2Init. Vulkan: criação de instância e dispositivo lógico confirmada no S25 Ultra, Adreno 830, API 1.3.284. Isso não valida o renderer do jogo. Sem confirmação de menu, gráficos, áudio, saves reais ou jogabilidade.

## Reproduzir a geração

Os pacotes locais foram extraídos com cdecrypt, usando sempre um diretório de destino separado; as pastas em Downloads não foram modificadas.

Se for necessário refazer a cópia efetiva, use um novo diretório vazio de saída:

```powershell
python tools/prepare_game.py --base work/extracted/base --update work/extracted/update --output game-new --manifest local-reports/game-new-manifest.json
python tools/audit_rpx.py --game game-new --upstream upstream --output local-reports/rpx-new-audit.json
```

Para gerar novamente o C, use um novo diretório vazio:

```powershell
python tools/patch_reference.py upstream
python tools/recompile.py --output build/gen-new
```

O gerador recusa um executável com SHA-256 diferente do perfil identificado. Não selecionar a edição USA de Zelda para contornar essa verificação.

Para compilar o C inicial com as ferramentas já instaladas:

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_android.ps1
```

Esse comando usa SDK `C:\Android\Sdk`, NDK `30.0.16248370`, CMake `4.1.2`, Android API 33 e ABI `arm64-v8a`. Esses são os parâmetros do protótipo, não uma lista de aparelhos já compatíveis.

Testes existentes do upstream:

```powershell
python -m unittest discover -s upstream/tools/recomp -p test_builds.py
```

## Executar o diagnóstico

A versão nativa verifica o SHA-256 do RPX antes de carregar a memória, configura os imports de dados e inicia as threads de Captain Toad. Sem renderer, áudio, snapshots ou hooks de Zelda. Uma API ausente encerra o diagnóstico com código 78; um limite de 10 segundos encerra com 124.

Windows, usando o Clang/MSYS2 e o CMake instalados:

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_windows.ps1
build/windows-diagnostic/ct-diagnostic.exe --game game --seconds 10
```

Android, com depuração USB autorizada. Informe o identificador local de `adb devices`; não o publique:

```powershell
powershell -ExecutionPolicy Bypass -File tools/build_android.ps1
powershell -ExecutionPolicy Bypass -File tools/run_android_diagnostic.ps1 -Serial <identificador-local> -Mode Vulkan
powershell -ExecutionPolicy Bypass -File tools/run_android_diagnostic.ps1 -Serial <identificador-local> -Mode Boot
```

O script usa exclusivamente `/data/local/tmp/captain-toad` e seleciona o dispositivo explicitamente. Os logs ficam em `local-reports/`, fora do Git. Não é necessário instalar APK para esse diagnóstico. O executável contém código recompilado do jogo e permanece local; não criar releases com ele.

Outros modos do script: `SelfTest`, `Mutex`, `Filesystem`, `System` e `Verify`. Testes de filesystem usam conteúdo e save sintéticos, separados dos arquivos do jogo.

Estado da validação em 10/10/2026:

- Cinco testes CTest passaram no Windows: vetores SHA-256, mutex com concorrência no mesmo núcleo emulado, leitura/escrita/limites de filesystem, MCP/UC e recusa de RPX desconhecido.
- No S25 Ultra passaram os testes nativos de SHA-256, fast mutex, filesystem e MCP/UC. O teste Vulkan criou uma instância e um dispositivo lógico.
- Após as APIs de startup serem implementadas, o boot chegou a `gx2.GX2Init`. Inicialização gráfica e renderização permanecem pendentes.

## Próxima etapa: GX2 e renderer Vulkan

Integrar as APIs GX2 e a fila de rendering genérica, separando as dependências de mods, câmera e interpolação de Zelda. Começar pela primeira chamada real, `GX2Init`, e avançar até a primeira imagem. Depois integrar áudio, controles, saves reais e embalagem do APK.

Limitações atuais: `_iob` ainda não tem ABI de streams implementado; callbacks importados de exceção/atexit permanecem nulos; palavras de opcode 0 e chamadas indefinidas continuam explícitas; só três chaves UC são suportadas, com inglês como idioma inicial e região EU. Configurações desconhecidas param o diagnóstico. Filas de posse/priority inheritance de fast mutex e saves de estado ainda não foram implementados.

A decompilação Switch pode ajudar a nomear funções equivalentes, mas não foi incorporado código desse projeto.

## Licença e créditos

Ferramentas e alterações deste projeto: MPL-2.0, conforme `LICENSE`. A base de recompilação/runtime é ZeldaWWHDRecomp e conserva sua licença e seus créditos no checkout separado; ver `THIRD_PARTY_NOTICES.md`.

Projeto de fãs independente, sem afiliação com a Nintendo. Os nomes dos jogos e consoles identificam a compatibilidade pretendida. Este repositório publica ferramentas, metadados de identificação e documentação; os arquivos do jogo e seu código gerado permanecem locais.
