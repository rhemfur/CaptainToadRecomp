# Ambiente de teste Android

Alvo inicial: Samsung Galaxy S25 Ultra (SM-S938B), consultado via ADB em 10/10/2026.

| Item | Valor observado |
|---|---|
| Android | 16, API 36 |
| ABI | arm64-v8a |
| SoC | Qualcomm/QTI SM8750 |
| GPU | Adreno 830 |
| Versão Vulkan anunciada pelo sistema | 1.3.0 |
| ADB | Conectado e autorizado |

O protótipo de código ARM64 usa Android API 33 como nível mínimo de compilação. Não é necessário mudar esse mínimo apenas porque o aparelho roda API 36.

O boot de diagnóstico foi executado no aparelho até GX2Init, e a criação básica de instância/dispositivo Vulkan passou. Ainda faltam o renderer do jogo, desempenho, jogabilidade e integração do APK.

Quando houver mais de um dispositivo conectado, selecionar explicitamente o celular em todos os comandos: `adb -s <serial-local> ...`. O identificador do aparelho fica apenas em `local-reports/device-target.json`, excluído do Git; não publicá-lo.

Próxima validação no aparelho: inicialização da aplicação, criação do dispositivo Vulkan e coleta de logs de falhas. Em seguida, menu e primeira fase, áudio, toque/controle, save/load e pausa/retomada. Registrar resultados medidos; não inferir FPS a partir de outro jogo.

## Marco de diagnóstico de boot — 10/10/2026

O código recompilado entrou no boot no Galaxy S25 Ultra e no Windows. As primeiras dependências foram resolvidas com serviços de debugger/clocks, OSFastMutex, filesystem e MCP/UC. O boot atual chega a `gx2.GX2Init`; ainda não há imagem ou APK jogável.

No S25 Ultra, criação de instância Vulkan 1.3 e dispositivo lógico foi verificada, com Adreno 830 reportando API 1.3.284. Passaram testes de SHA-256, concorrência/recursão de mutex, arquivos/saves sintéticos e registros MCP/UC. Cinco testes CTest também passaram no Windows; os 17 testes existentes do recompilador passaram. Logs e binários são locais e não foram publicados.

Próximo trabalho: integrar GX2 e o renderer Vulkan para chegar à primeira imagem. Consultar README para os comandos reproduzíveis e limitações atuais.
