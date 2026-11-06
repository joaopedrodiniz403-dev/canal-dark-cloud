# Agente de nuvem Nuvem Escura

## Duas funções

O agente agendado do Codex retoma o trabalho de engenharia: lê este repositório, verifica CI e materiais disponíveis, implementa a próxima etapa executável, testa, corrige e registra evidências. Suas instruções duráveis estão em `AGENTS.md`. Ele não é um servidor 24 horas nem uma declaração de que o produto inteiro está pronto.

O workflow de produção do GitHub Actions executa o pipeline de vídeo em runner Linux. Os workflows são código revisável; schedules só ficam ativos na branch padrão. Uma execução agendada pode atrasar por limites da plataforma. Serviços pagos e publicação pública não estão autorizados.

## Aquisição dos projetos

`agent/upstreams.lock.json` registra oito repositórios e commits fixos. `Baixar repositorios auditaveis` baixa snapshots reais e entrega oito artifacts `fonte-*`, com tar.gz, origem, commit e SHA-256. Licenças originais ficam preservadas. Dependências, submódulos e objetos Git LFS não são instalados/obtidos recursivamente. Arquivos que o próprio upstream versionou fazem parte do snapshot.

Só o Chopify é o backend selecionado para integração nesta etapa. Baixar código não significa que todos os produtos foram integrados, testados ou que seus modelos/vozes possuem licença adequada.

## Ordem de trabalho do agente

- Conferir última execução CI e downloads; reparar falhas reproduzíveis.
- Validar corte real com fala em mídia autorizada. Sem essa entrada, avançar testes, ingestão e infraestrutura; não gerar falsa amostra.
- Completar ingestão segura de mídia, persistência de estado e deduplicação.
- Implementar pesquisa e seleção semântica/visual em português, com análise de contexto e reação.
- Construir originais com recursos gratuitos e licenças verificadas; documentar hardware e qualidade.
- Integrar fila editorial e YouTube privado/OAuth, depois métricas reais quando houver autorização de acesso.

## Dependências ainda não fornecidas

O ambiente atual não possui credenciais YouTube, acesso a armazenamento de mídia nem lista de gravações autorizadas. O cadastro de fontes está vazio. Portanto, criar o agente e agendar execução não libera cinco Shorts reais por dia automaticamente. Ele deve informar esses bloqueios e continuar o desenvolvimento possível.

Não cadastre tokens ou links assinados no repositório público. Referências de licença devem apontar para evidência conferida pelo responsável, sem expor documentos privados.
