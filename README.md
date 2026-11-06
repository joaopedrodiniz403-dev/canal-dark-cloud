# NUVEM ESCURA AI — motor de cortes v2

Primeira implementação de cortes a partir de arquivos locais com direitos atestados pelo operador. Sem serviços pagos e sem publicação no YouTube. A qualidade editorial exige revisão; não há promessa de viralização.

## Executar

Requer Python 3.11+, FFmpeg com libass/libx264 e fontes DejaVu. Para transcrição automática em português, instale `python -m pip install -r requirements-cuts.txt` (faster-whisper CPU/int8). O primeiro uso baixa o modelo `small`, exige rede e espaço; uma GPU não é obrigatória. Transcrição pode ser lenta em lives longas. Não usamos eSpeak ou slides como alternativa.

1. Coloque vídeo próprio/licenciado e, opcionalmente, transcrição em `media/authorized/`.
2. Cadastre a fonte em `agent/sources.json`, conforme [formato de entrada](docs/INPUT.md).
3. Execute `python -m nuvem.engine` ou `python agent/produce.py`.
4. Abra `output/cuts/REVIEW.md` e `review_queue.json`. Cada diretório contém MP4, palavras sincronizadas, ASS, timeline, log FFmpeg e relatório.

Uma fila vazia gera relatório `EMPTY_QUEUE`, sem fabricar vídeos. Fonte inválida fica `BLOCKED`. Saída aprovada tecnicamente fica `PENDING_HUMAN_REVIEW`; conteúdo sintético de teste fica `TECHNICAL_TEST_ONLY`. Nenhum destes estados autoriza publicação.

## O que funciona

- Bloqueio por ausência de atestado e referência de direitos; caminhos confinados e proteção contra symlinks externos.
- ASR word-level com faster-whisper ou transcrição fornecida, validada por timestamps.
- Candidatos por frases completas, duração 12–59 s, ranking heurístico explicável em português, supressão de sobreposição.
- Remoção de pausas longas com margem de respiração e remapeamento de legendas.
- 1080×1920/30 fps, cena inteira sobre fundo desfocado, áudio original normalizado, legendas curtas com palavra ativa em destaque e marca Nuvem Escura.
- QA de decodificação, duração, dimensões, áudio ausente/inaudível/clipping, congelamento, preto e limites temporais das legendas.
- SQLite com hash da fonte, trecho, texto e limite de cinco saídas por dia em São Paulo. Execute somente um produtor por banco; o workflow usa `concurrency`.

## Automação e limites

O workflow `agent.yml` está preparado para 13:23 UTC / 10:23 em São Paulo, diariamente, após integração na branch padrão. O GitHub pode atrasar agendas. Atualmente não há mídia cadastrada. Arquivos ignorados pelo Git não chegam ao runner: disponibilize somente mídia autorizada no checkout ou adicione uma integração privada de armazenamento antes da produção em nuvem. Não coloque tokens nem documentos privados no repositório público.

O histórico é restaurado por Actions Cache. Cache pode expirar/ser removido: a deduplicação entre execuções só é garantida enquanto o banco persistir. Para uma operação contínua, será necessário armazenamento durável do SQLite e da mídia. Artifacts de revisão expiram após sete dias. Não rodamos download de streamers nem serviços pagos.

## Verificar

```sh
python -m unittest discover -v
python -m tests.demo
```

Os testes renderizam vídeo com movimento e tom de teste, verificam QA e rejeição de áudio silencioso, direitos, caminhos, legendas, timestamps e deduplicação. O demo **não contém fala nem é um Short publicável**: não comprova ASR, qualidade narrativa ou comparação profissional.

Veja [auditoria](docs/AUDIT.md), [evidências e pendências](docs/VALIDATION.md). Rastreamento facial, seleção semântica multimodal, pesquisa de tendências, geração original, YouTube e aprendizado por métricas continuam pendentes. `main.py` e `agent/produce.py` agora chamam o motor real; os geradores antigos de slides foram substituídos.

## Correção do fluxo de testes e backend existente

Fixtures sintéticas são rejeitadas por padrão na produção. Testes internos exigem permissão de código explícita, ficam `INTERNAL_TESTS_ONLY`, não recebem pontuação editorial e não entram na fila de conteúdo. Os relatórios registram `editorial_approved: false` e `publication_approved: false`. O CI deixou de oferecer o padrão colorido como artifact de vídeo.

O [backend Chopify](docs/CHOPIFY.md) foi preparado para utilizar um projeto existente de verdade, com revisão fixa e entrada local autorizada. Sua execução completa com material real ainda está pendente; não é a produção diária padrão.
