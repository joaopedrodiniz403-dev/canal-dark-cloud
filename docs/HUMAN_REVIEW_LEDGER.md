# Histórico durável de revisão humana

O ciclo antes guardava hashes de deduplicação, mas os itens aguardando revisão ficavam só no relatório/artifact do runner. A seção opcional `reviews` do estado schema 1 agora preserva os descritores na mesma branch `nuvem-state`, usando o lease já existente. Estado antigo permanece legível sem inventar revisão para vídeos históricos. Não é armazenamento de mídia: um artifact expirado não é recuperado por possuir seu hash.

Um item técnico elegível registra somente hashes SHA-256 de MP4/SRT/fonte, revisão do backend, data, status e eventos de decisão. Não salva caminhos privados, nomes de arquivos, documentos de direitos, URLs assinadas, tokens ou justificativas livres. As chaves são fechadas; campos desconhecidos ou aprovação de publicação causam erro de validação, sem zerar histórico. Todos os dados versionados em repositório público devem poder ser públicos, inclusive o identificador GitHub do revisor.

A fila durável começa em PENDING_HUMAN_REVIEW. Decisões explícitas geram eventos numerados e status EDITORIAL_APPROVED ou EDITORIAL_REJECTED. A operação exige MP4 e SRT locais, hashes correspondentes, identificação do responsável, código de motivo e número esperado de eventos. Pode rejeitar uma aprovação anterior mantendo ambos os eventos. O conflito de eventos local e o lease remoto protegem contra gravações desatualizadas; mudanças de mídia exigem um item novo. publication_approved permanece sempre falso. Nenhum upload/agenda/publicação foi conectado.

## Uso pelo responsável, depois de assistir e conferir direitos

Baixe/restaure os arquivos por um canal autorizado. Em contexto privado com acesso já configurado, obtenha estado/lease pela CLI existente antes de alterar qualquer decisão:

```sh
python -m nuvem.github_state pull
python -m nuvem.review_ledger list
python -m nuvem.review_ledger decide --id HASH_DO_VIDEO --video /caminho/clip.mp4 --srt /caminho/clip.srt --action reject --reason-code ASR_ERRORS --reviewer SEU_USUARIO_GITHUB --expected-events 0 --confirm-human-review
python -m nuvem.github_state push
```

Para aprovação editorial use `--action approve --reason-code CONTENT_REVIEWED`, apenas após a revisão humana real. A flag confirma uma declaração do operador, não autentica a identidade nem comprova que assistiu ao vídeo. Autenticação, controle de acesso e autorização de gravação dependem do ambiente/GitHub e continuam necessários. Não há aprovador por IA, assinatura criptográfica ou portal pronto. Quem possui escrita no estado continua sendo parte da fronteira de confiança.

Não informe tokens em chat/argumentos: use GH_TOKEN pelo mecanismo autorizado e GITHUB_REPOSITORY conforme a CLI existente. Sem credenciais/mídia privadas, não execute uma decisão positiva para simular operação. O CI só lê o estado remoto e testa contratos com doubles; nunca aprova conteúdo real.

## Integração e limites atuais

O ciclo anexa `review_id` ao item e persiste `reviews` junto com orçamento/deduplicação. Execuções seguintes informam `durable_pending_reviews`, mesmo se a fonte já foi processada ou o cadastro estiver vazio. Falhas técnicas não entram no registro; falta de SRT não pode produzir revisão válida. Não há referência de mídia durável recuperável até configurar armazenamento privado. Também não há armazenamento privado configurado ou OAuth YouTube.

Código em PR, ainda não ativado na branch padrão. A validação de perda de histórico e ingestão de mídia no PR #2 permanece separada. Não migrei nem escrevi decisões no estado de produção nesta execução. Diagnósticos do filme rejeitado pelo seletor continuam fora da fila.
