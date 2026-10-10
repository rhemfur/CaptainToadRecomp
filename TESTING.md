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

Esses dados confirmam os requisitos básicos do alvo. Ainda não há validação de boot, renderer Vulkan do projeto, desempenho ou jogabilidade de Captain Toad no aparelho. O APK e o runtime ainda precisam ser integrados.

Quando houver mais de um dispositivo conectado, selecionar explicitamente o celular em todos os comandos: `adb -s <serial-local> ...`. O identificador do aparelho fica apenas em `local-reports/device-target.json`, excluído do Git; não publicá-lo.

Próxima validação no aparelho: inicialização da aplicação, criação do dispositivo Vulkan e coleta de logs de falhas. Em seguida, menu e primeira fase, áudio, toque/controle, save/load e pausa/retomada. Registrar resultados medidos; não inferir FPS a partir de outro jogo.
