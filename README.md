# NUVEM ESCURA AI

Sistema em desenvolvimento para cortes autorizados e fila de revisão. Não é uma fábrica profissional concluída. Sem mídia autorizada, registra bloqueio e não fabrica vídeos de demonstração. Publicação pública permanece desativada.

## Nuvem

- **Baixar repositorios auditaveis:** snapshots fixos de oito projetos, com licenças, commit e SHA-256. Não instala ou executa os projetos baixados. Os artifacts `fonte-*` expiram após 30 dias.
- **Nuvem Escura - ciclo de nuvem:** GitHub Actions diariamente às 13:23 UTC / 10:23 em São Paulo, após integração na branch padrão, ou manualmente. Usa o pipeline real Chopify, até cinco saídas por dia e revisão humana obrigatória. Sem fontes cadastradas gera `BLOCKED_NO_AUTHORIZED_MEDIA`.
- **Validar motor de cortes:** testes unitários, renderização técnica real e importação do CLI upstream. Testes sintéticos são internos, não vídeos para o canal.

O coordenador usa `nuvem/cloud_cycle.py`; o estado durável fica em `.nuvem/state.json` na branch separada `nuvem-state`. Contém hashes/datas/contagens, sem segredos. Acesso ao estado usa o token temporário do Actions. Se leitura ou gravação falhar, a execução falha; não zera histórico por erro de rede. Vídeos e relatórios de revisão expiram após sete dias: armazenamento privado durável de mídia ainda precisa ser integrado.

O agente recorrente do Codex é separado do workflow de vídeo. Suas instruções estão em [AGENTS.md](AGENTS.md) e [CLOUD_AGENT.md](docs/CLOUD_AGENT.md). A tarefa recorrente foi criada e ativada para retomar o trabalho diariamente pela manhã, por volta das 8h de São Paulo, a partir de 7/11/2026. A primeira execução do agente ainda não foi observada. O workflow GitHub é independente dessa tarefa.

## Conteúdo de verdade

1. Disponibilize gravação própria/licenciada com fala em `media/authorized/`.
2. Cadastre direitos em `agent/sources.json`, conforme [INPUT.md](docs/INPUT.md).
3. Siga [CHOPIFY.md](docs/CHOPIFY.md) para instalar somente o backend selecionado.
4. Revise contexto, recorte, sincronismo, título, direitos e qualidade dos MP4 reais.

Arquivos de mídia são ignorados pelo Git e não chegam automaticamente ao runner. Não coloque documentos privados ou tokens no repositório público. Sem integração de armazenamento ou fonte disponível no checkout, a produção em nuvem continua bloqueada.

O caminho Chopify faz ASR CPU, análise de candidatos com evidências de áudio/imagem, rastreamento facial do upstream, legendas, cortes de pausas e tratamento de áudio. O ciclo aplica QA técnico e encaminha saídas aprovadas tecnicamente para `PENDING_HUMAN_REVIEW`. Não há aprovação editorial automática validada. Pontuação é heurística e não promete viralização.

O motor menor `python -m nuvem.engine` continua disponível para experimentos locais com FFmpeg e transcrição word-level, mas não é a produção diária selecionada. Nunca usa eSpeak ou slides como fallback.

## Verificação e pendências

```sh
python -m unittest discover -v
```

22 testes locais passaram na implementação do ciclo de nuvem. Os testes de orquestração usam um backend controlado para verificar regras; o teste de renderização realmente invoca FFmpeg. Isso não comprova um Short profissional com fala real.

Pesquisa de tendências, criação de originais com movimento/TTS neural, seleção semântica em português, avaliação editorial por IA, armazenamento privado, YouTube/OAuth e métricas permanecem em desenvolvimento. Consulte [auditoria](docs/AUDIT.md) e [evidências](docs/VALIDATION.md).
