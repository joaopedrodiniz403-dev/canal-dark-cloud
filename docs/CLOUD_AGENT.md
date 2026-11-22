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

## Estado desta configuração

O download dos oito snapshots foi executado com sucesso: https://github.com/joaopedrodiniz403-dev/canal-dark-cloud/actions/runs/42239811705 (oito artifacts confirmados).

A primeira tentativa encontrou o limite de cinco tarefas. Após o usuário autorizar a pausa de uma tarefa existente, a criação foi confirmada: Agente Nuvem Escura ativo, diariamente pela manhã, por volta das 8h de São Paulo, a partir de 7/11/2026. As instruções cobrem engenharia, produção, testes e evolução do projeto. A seleção de ambiente foi retornada como herdada, sem detalhes; não houve ainda execução observada do agente nem confirmação de uma sessão futura de nuvem. O ciclo GitHub é independente e tem runner de nuvem explícito.

O ciclo GitHub usa o backend Chopify e estado versionado na branch `nuvem-state`, em lugar de depender do cache. A produção fica serializada por concurrency. O estado carrega hashes de fontes processadas/vídeos e contagens por dia em São Paulo; não armazena tokens. Read/write com erro ou conflito interrompe a operação. Após integração do workflow na branch padrão, a primeira execução verifica esse armazenamento na nuvem e gera relatório, mesmo com fila vazia.

## Validação real registrada em 9/11/2026

As execuções de engenharia foram observadas no ambiente herdado. Os PRs #2 e #3 seguem abertos. Um diagnóstico real com atores/diálogo da obra CC BY Tears of Steel foi executado, sem alimentar o canal. Corrigidos o conflito PyAV19/faster-whisper e o tratamento de zero candidatos; a seleção rejeitou o trecho (5,03 < 8), e a inspeção mediu erros de fala e enquadramento. Veja `REAL_MEDIA_VALIDATION.md` e `runs/2026-11-09.md`. Isso não representa aceite editorial, teste em português/GTA RP nem autorização de publicação.
