# Captain Toad EUR — protótipo de recompilação para Android

Projeto iniciado em `C:\DEV\Captain Toad` em 10/10/2026. O alvo inicial é a edição Wii U EUR com update interno v16. A primeira etapa identifica, traduz e compila o executável para Android ARM64; ainda não executa o jogo e não produz APK.

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

Os diretórios de saída da preparação e da geração devem estar vazios. Os comandos geram uma biblioteca estática local; ainda não um aplicativo executável.

## Estrutura

- `tools/`: preparação da cópia atualizada, auditoria do RPX, geração de C e build ARM64.
- `profiles/captain-toad-eur-v16.json`: identificação por SHA-256 do RPX atualizado, sem hooks de Zelda.
- `upstream/`: checkout local de ZeldaWWHDRecomp, mantido como referência e ignorado no repositório deste projeto.
- `work/extracted/base` e `work/extracted/update`: extrações separadas dos pacotes originais.
- `game/`: cópia efetiva, com os arquivos do update sobre os caminhos correspondentes da base.
- `local-reports/`: manifesto de cópia e auditoria detalhada dos imports.
- `build/gen/`: C gerado localmente do jogo.
- `build/android-gamecode/`: objetos e biblioteca estática ARM64.

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

Não há confirmação de boot, menu, gráficos, áudio, saves ou jogabilidade em Android. A biblioteca estática pode conter referências externas não resolvidas; a ligação com o runtime é uma etapa separada.

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

## Próxima etapa: runtime específico de Captain Toad

1. Separar o loader e a inicialização genérica das suposições de Zelda: nome RPX, perfil, memória, dados importados, save paths e entry point.
2. Remover dependências dos arquivos de câmera, interpolação, mods e hooks de Zelda da composição do runtime Captain Toad.
3. Registrar APIs não implementadas com erro explícito no protótipo. O `hle_unimplemented` atual de Zelda retorna zero após registrar a chamada; isso pode mascarar sucesso e precisa ser revisto para a fase de diagnóstico.
4. Priorizar as lacunas verificadas: fast mutex/serviços coreinit, estado GX2, áudio AX/AXFX, microfone, amiibo e integração de saves. Não implementar todas como funções vazias; reproduzir o comportamento necessário com referência e testes apropriados.
5. Fazer boot de diagnóstico e obter menu/primeira fase no desktop antes da integração do APK. Depois validar toque, controles, pausa/retomada e saves no aparelho alvo.

A decompilação Switch pode ajudar a nomear e entender funções equivalentes, mas não é uma implementação completa usada por este protótipo.

## Licença e créditos

Ferramentas e alterações deste projeto: MPL-2.0, conforme `LICENSE`. A base de recompilação/runtime é ZeldaWWHDRecomp e conserva sua licença e seus créditos no checkout separado; ver `THIRD_PARTY_NOTICES.md`.

Projeto de fãs independente, sem afiliação com a Nintendo. Os nomes dos jogos e consoles identificam a compatibilidade pretendida. Este repositório publica ferramentas, metadados de identificação e documentação; os arquivos do jogo e seu código gerado permanecem locais.
