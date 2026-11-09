# Diagnóstico com mídia licenciada e fala real

Esta validação usa uma cena do filme **Tears of Steel**, com atores e áudio natural em inglês. Não usa texto sobre fundo gráfico nem áudio sintético. É um diagnóstico do backend, não um Short aprovado para o canal.

## Direitos e reprodução

A [página oficial de compartilhamento](https://mango.blender.org/sharing/) licencia os resultados do Mango Open Movie Project em CC BY 3.0, com atribuição `(CC) Blender Foundation | mango.blender.org`, ressalvando logotipos e material externo. A [página oficial de download](https://mango.blender.org/download/) liga o filme e as legendas. O arquivo `copyright.txt` do diretório se refere especificamente aos arquivos avulsos da trilha sonora, sob CC BY-ND; estes não são utilizados separadamente. O diagnóstico usa o filme licenciado com seu áudio integrado, sem importar música externa, e informa as modificações.

O arquivo completo 720p é conferido por SHA-256 antes de qualquer processamento:

`efa9062d9cdb7a338e40ad530dfdf234806743f29ae6a1a136b97ece4e588e8f`

A cena é 00:22–00:46, escolhida pela conversa inicial completa nas legendas oficiais, não por um intervalo aleatório. O arquivo original não entra no repositório ou no artifact. Não se altera `agent/sources.json` nem o estado de produção.

```sh
python -m pip install -r work/chopify/requirements.txt -c requirements-cuts.txt
HF_HOME="$PWD/work/hf-cache" python -m nuvem.real_validation --download
```

Use a revisão Chopify fixada em `docs/CHOPIFY.md`. Requer CPU/RAM/espaço para o modelo small e o filme (~372 MB). Não usa API paga nem GPU. O workflow `real-media-validation.yml` executa esse teste em PR/manual, sem schedule e sem escrita no repositório. Artifacts expiram em sete dias.

## O que é medido

- ASR real `small`/CPU/int8, língua detectada e quantidade de palavras.
- WER do texto normalizado contra as falas iniciais da legenda oficial inglesa (sem o cartão não falado “Fourty years later”). Nomes próprios e contrações afetam o indicador; não é medida de sincronismo nem de qualidade em português.
- Seleção automática preservando o mínimo de **8/10**. Rejeição de candidatos não reduz esse limite e não aprova vídeo.
- Render diagnóstico separado do melhor candidato para inspecionar recorte, legendas, pausas e áudio, mesmo se esse candidato foi rejeitado. Esse modo nunca entra na fila de produção e nunca autoriza publicação.
- Amostras de detecção facial, sem alegar identificação do falante ativo. O maior rosto não equivale ao interlocutor correto.
- QA técnico de resolução, duração, decodificação, áudio, congelamento, preto e limites temporais das legendas.

O MP4 tem marca “DIAGNOSTIC - NOT APPROVED”, crédito visível e metadados de atribuição. O JSON mantém `production_eligible`, `editorial_approved` e `publication_enabled` falsos. O arquivo de metadados também registra que não foi aprovado. **Um diagnóstico concluído pode conter reprovações de qualidade:** leia os resultados, não apenas a cor verde do workflow.

## Falhas reais corrigidas e resultados

1. O preflight antigo passava, mas faster-whisper 1.2.1 falhava ao decodificar com PyAV 19 (`metadata_errors` removido). `requirements-cuts.txt` fixa av 16.0.1; produção e validação aplicam essa restrição. O CI agora executa o decodificador real, sem precisar baixar um modelo para esse teste pequeno.
2. O Chopify retorna código 1 quando nenhum candidato atinge 8/10. O adaptador reconhece exclusivamente essa rejeição concluída, com seleção/projeto/segments/log coerentes, e retorna `NO_CANDIDATES`. Traceback de ASR, render com falhas ou seleção antiga não viram falso sucesso.

Em 9/11, a transcrição real produziu 68 tokens word-level. WER normalizado: **16% (12 erros / 75 unidades de referência)**. Score do candidato: **5,03/10**, abaixo de 8; **zero saídas automáticas**. O render diagnóstico durou ~20,92 s em 1080×1920 e passou nas oito verificações técnicas. Houve rosto detectado em 76 de 104 amostras, mas o crop também manteve uma pessoa enquanto a outra falava. Transcrição e enquadramento **não receberam aprovação editorial**.

Falta validar/corrigir o comportamento em português e GTA RP, rastreamento de falante, transcrição em música/ruído e seleção semântica. Este teste real não conclui os critérios do sistema profissional.
