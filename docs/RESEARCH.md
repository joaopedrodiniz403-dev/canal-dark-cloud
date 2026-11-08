# Pesquisa verificável de pautas

`python -m nuvem.research` consulta RSS públicos do Google News e Google Trends Brasil, sem API paga, chave, LLM ou dependência adicional. A configuração está em `agent/research.json`; termos incluem GTA RP/FiveM e os criadores indicados pelo titular do canal.

## Saídas e critérios

`output/research/research.json` contém títulos relacionados, termos correspondentes, links dos itens e feeds, publisher quando declarado, data de publicação declarada no RSS, horário de coleta e SHA-256 da resposta. `RESEARCH.md` permite revisar os achados. A data é evidência do feed, não confirmação da data do acontecimento ou da veracidade da manchete. Links do Google News podem ser de agregador; o corpo do artigo não foi verificado.

Só entram manchetes com correspondência por palavra/frase, timestamp com fuso, até sete dias de idade e sem data mais de dez minutos no futuro. Manchetes repetidas são agrupadas com preservação das fontes. O score mede apenas correspondência lexical e frescor, com componentes registrados; não mede audiência, retenção, humor, potencial real de engajamento ou viralização. Não há métricas de YouTube inventadas.

Feed acessível sem correspondência produz `NO_RELEVANT_CANDIDATES`, sem preencher a lista com pautas genéricas. Falha de todas as fontes produz `FAILED`; falha parcial produz `PARTIAL`, preserva achados disponíveis e retorna código de erro para sinalizar o problema. XML inválido, entidades/DOCTYPE, corpo maior que 2 MiB e destinos de coleta fora dos endpoints previstos são rejeitados. Erros públicos usam códigos fixos.

## Operação na nuvem

O workflow `research.yml` roda em PRs desta funcionalidade, manualmente e, após aprovação/integração à branch padrão, diariamente às 12h UTC / 9h em São Paulo. Requer somente leitura do repositório. Seus artifacts `nuvem-pesquisa-*` expiram em 14 dias. Isso ainda não representa memória permanente de pesquisa entre execuções; os snapshots de evidência desta entrega ficam versionados.

```sh
python -m unittest tests.test_research -v
python -m nuvem.research --config agent/research.json --output output/research
```

## Limites editoriais e de direitos

Todo candidato fica `production_eligible: false`, `reuse_rights_verified: false` e `editorial_review_required: true`. A pesquisa não altera `agent/sources.json`, não baixa vídeos/áudio/imagens, não cria roteiros a partir de notícias não verificadas e não publica. Uma pauta pode orientar apuração de um roteiro próprio; não concede direitos sobre a transmissão ou sobre o artigo encontrado.

A próxima etapa é confirmar informações em fontes primárias e ligar pautas a material autorizado. Pesquisa semântica multimodal, compreensão de humor/reação e feedback por métricas reais ainda não foram implementados.
