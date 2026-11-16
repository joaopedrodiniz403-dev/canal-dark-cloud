# Preparação verificável de upload privado

`nuvem.youtube_private_plan` prepara um pedido para a API oficial YouTube. Não executa OAuth, HTTP, transferência, publicação ou agendamento. É uma etapa revisável anterior ao transporte, não integração YouTube concluída.

## Contrato

O plano exige item EDITORIAL_APPROVED no histórico, fonte conhecida, hashes MP4/SRT exatos, confirmação explícita de revisão dos metadados, público infantil declarado e canal esperado. Verifica contêiner MP4, vídeo vertical 1080×1920, áudio e duração 15–59,1 s. A aprovação se refere aos bytes do item; não substitui comprovação de direitos ou validação de fala.

O pedido usa POST no endpoint oficial `https://www.googleapis.com/upload/youtube/v3/videos`, `part=snippet,status`, `uploadType=resumable`, `notifySubscribers=false` e `status.privacyStatus=private`. Solicita futuramente o escopo OAuth `https://www.googleapis.com/auth/youtube.upload`. Nunca aceita privacyStatus/public/unlisted, publishAt ou credenciais nos metadados. O canal esperado é intenção do operador, não canal OAuth verificado; `oauth_channel_verified=false` permanece explícito.

Os metadados de entrada têm somente title, description, category_id e made_for_kids. Limites são validados localmente; disponibilidade da categoria e identidade real do canal ainda precisam da API autorizada. A revisão dos metadados é declaração do operador, sem autenticação própria. Alteração de bytes, metadados ou eventos de revisão invalida o plano na revalidação. Uma rejeição posterior bloqueia o plano anterior, mesmo que os arquivos sejam iguais.

## Saída privada

O comando grava o plano somente em `private/youtube-plans/`, ignorado pelo Git, com arquivo modo 0600 e sem sobrescrever arquivo existente. Inclui título e descrição potencialmente privados: não envie esse diretório a artifacts, logs ou repositório público. Links e tokens de sessão resumable não são gerados/armazenados nesta etapa. Stdout contém somente status e hash do plano; falhas não imprimem dados privados ou respostas do serviço.

```sh
python -m nuvem.youtube_private_plan --state work/cloud-state.json --id HASH_DO_VIDEO --video /caminho/clip.mp4 --srt /caminho/clip.srt --metadata private/metadata.json --expected-channel-id ID_UC_DO_CANAL --confirm-metadata-reviewed
```

O metadata.json deve conter os quatro campos citados e ser criado em local privado pelo responsável. O comando não lê tokens do ambiente. Não há pedido de credenciais em chat nem mudança em outras automações.

## Evidência e pendências

Testes de contrato usam mídia/probe e decisões humanas simuladas explicitamente como doubles. O estado real consultado em 16/11 está vazio e foi bloqueado com HUMAN_EDITORIAL_APPROVAL_REQUIRED; nenhum vídeo de teste/diagnóstico foi cadastrado como aprovado.

Um futuro executor precisa revalidar o plano, renovar OAuth pelo mecanismo seguro, confirmar o canal autorizado, implementar upload resumable e recuperação, deduplicação de uploads, contagem real no fuso America/Sao_Paulo, armazenamento privado, retorno de ID/estado e métricas. Precisa evitar reenviar automaticamente após resposta ambígua. O hash do plano não é garantia de idempotência da API. Não há upload externo de SRT, agendamento, métricas, contagem de uploads ou canal conectado nesta etapa.

A publicação pública continua exigindo autorização explícita independente; o planejador não permite habilitá-la. O limite de até cinco Shorts/dia permanece na produção existente; preparar planos não incrementa métricas ou uploads fictícios.

## Fontes oficiais consultadas em 16/11/2026

- videos.insert: https://developers.google.com/youtube/data/reference/rest/v3/videos/insert
- OAuth para aplicações nativas: https://developers.google.com/identity/protocols/oauth2/native-app

Ambas retornaram HTTP 200 pelo proxy/TLS herdados. Referências e hashes das páginas em docs/evidence/2026-11-16/official-docs.json. Os fluxos OAuth e de transferência documentados não foram executados, por ausência de credenciais e conteúdo real aprovado.
