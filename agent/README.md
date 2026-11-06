# Nuvem Escura AI v1

## Estado atual
Agente de producao experimental: ate 5 Shorts por execucao, ranking editorial heuristico e fila de revisao humana. Sem upload automatico.

## Rodar
GitHub > Actions > **Nuvem Escura AI - produzir 5 Shorts para revisao** > Run workflow.
Ao concluir, baixe o artifact e abra `review_queue.json`. Cada MP4 fica marcado `PENDING_HUMAN_REVIEW` quando passa validacao tecnica.

## Modos
- **Original:** cinco roteiros educativos demonstrativos em `agent/topics.json`. Conteudo grafico simples, voz espeak-ng. Nao e video generativo cinematico por IA; precisa de melhoria antes de publicar.
- **Corte autorizado:** coloque videos seus ou licenciados em `media/authorized/` e registre cada trecho em `agent/authorized_clips.json` com `path`, `start`, `end`, `title`, `approved_for_reuse: true`, `permission_reference` e `editorial_score`. Sem autorizacao, nao processa.

## Limites
Nao pesquisa lives automaticamente, nao detecta melhores momentos por IA, nao verifica juridicamente direitos e nao publica no YouTube. A pontuacao de 0-100 e uma heuristica editorial, nao uma previsao de viralizacao. A meta de cinco depende dos limites de execucao do GitHub Actions e da quantidade de conteudo disponivel. Nunca envie chaves de API para o repositorio publico.
