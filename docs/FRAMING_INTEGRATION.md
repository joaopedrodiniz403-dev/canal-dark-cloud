# Integração opcional de enquadramento após seleção

`framing_mode: "preserve_two_faces"` é uma opção por fonte autorizada. O padrão continua `native`. Cadastro de fontes permanece vazio; nenhum vídeo está aprovado ou publicado.

A seleção nativa do Chopify continua exigindo 8/10. `nuvem.framing_stage` confere origem da transcrição, intervalo e nota da exportação contra `project/segments.json`, antes de reenquadrar. Não promove candidatos rejeitados. Notas não finitas, intervalos divergentes e ausência de seleção são rejeitados.

Após seleção, retima áudio e palavras com o mesmo módulo fixado do Chopify, mede caixas de rostos, exige plano de duas faces estável e visibilidade geométrica amostrada >=95%. Renderiza com legendas, verifica respostas aos comandos FFmpeg e executa QA técnico. A ausência de evidência ou reprovação técnica retorna zero saídas para revisão. Falhas de execução propagam erro; não são ocultadas como rejeição editorial.

A saída fica em `framing/<hash>/render/review.mp4`, acompanhada de SRT e metadados com aprovação editorial/publicação falsas. Exportações nativas permanecem intactas, mas não são encaminhadas pela integração opcional. Apenas caminhos retornados e registrados em `review_queue.json` são itens de revisão; não publique arquivos encontrados varrendo diretórios. Os relatórios `framing_report.json` e `framing/<hash>/framing.json` explicam rejeições e QA. O ciclo preserva `FRAMING_REJECTED` sem consumir a cota de cinco revisões/dia.

Isso não identifica falante ativo nem valida qualidade editorial. Identidade, oclusões, cruzamentos, gameplay/webcam e transcrição portuguesa precisam de validação real. Não se deve ativar esta composição indiscriminadamente em GTA RP. O cadastro deve permanecer sem esta opção até a composição ser escolhida na revisão de mídia autorizada.

## Evidência disponível

Em 12/11, executado novamente o backend fixado, modelo small, CPU, fala original da cena licenciada de Tears of Steel com a opção ligada. Resultado: 5,03/10, zero candidatos acima de 8, `NO_CANDIDATES`, `NOT_RUN_NO_CANDIDATES`, zero saídas. O teste confirma que a integração não contorna a seleção; não comprova um fluxo positivo editorialmente válido.

Os testes de contrato positivos usam doubles explicitamente identificados. A comparação de renderização com mídia real continua documentada em FRAMING_COMPARISON.md, apenas como diagnóstico de candidato rejeitado. Falta um trecho real aprovado pelo seletor e pela revisão humana para validar a integração positiva completa.

O workflow real executa a opção no diagnóstico licenciado e entrega `upstream_report.json`. Não altera fontes, estado ou publicação do canal.
