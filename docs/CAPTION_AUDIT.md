# Auditoria de exportação de legendas

Oito verificações técnicas de vídeo não bastam para avaliar legendas. O ciclo anterior verificava limites de tempo com texto substituto, sem conferir as palavras exportadas. A nova etapa `nuvem.caption_audit` valida o SRT real depois do render nativo ou da composição opcional e antes de encaminhar saídas à fila.

## Política inicial explícita

- SRT completo: sequência de blocos válida, texto presente, tempos válidos e sem markup não suportado. Blocos inválidos não são silenciosamente descartados.
- Sem sobreposição, início >=0 e final dentro do vídeo, com tolerância de arredondamento de 50 ms.
- Exibição por pelo menos 300 ms; máximo 25 caracteres/segundo, incluindo espaços; até duas linhas de 42 caracteres.
- Texto exportado igual à sequência de palavras ASR remapeadas após remoção de pausas. Ignora caixa e pontuação, normaliza Unicode, preserva diferenças lexicais e acentos (avó não é avô).
- Início/fim de cada cue coerentes com primeira/última palavra, tolerância de 150 ms. Verifica duração do vídeo contra o remapeamento.

Os limites são uma política conservadora inicial do projeto, não uma medição de percepção nem validação editorial. A comparação com ASR detecta erros de exportação, não erros cometidos pelo ASR. Não há OCR para conferir pixels/área ocupada pela legenda queimada. Tipografia, contraste, zona segura e sincronismo percebido ainda exigem revisão visual e escuta.

## Integração e relatórios

`chopify_backend.execute` confere metadados, origem e seleção nativa, remapeia palavras usando o módulo do commit fixado do Chopify e audita a saída final. Apenas itens que passam são retornados ao ciclo. Zero itens resulta em `CAPTIONS_REJECTED`; o ciclo preserva motivo/relatório sem consumir a cota ou marcar fonte como concluída. Falhas de execução continuam falhas.

`caption_report.json` contém políticas, número das cues com problema, medidas, correspondência de referência e hashes do MP4, SRT e transcrição. Nenhuma aprovação editorial/publicação é atribuída. A fila continua sendo exclusivamente de revisão humana.

Não reescrevemos somente o SRT: isso criaria divergência com a legenda queimada no vídeo. Corrigir velocidade exigirá adaptar agrupamento/duração e renderizar novamente o ASS/SRT em conjunto, com fidelidade à fala. O novo gate bloqueia os problemas conhecidos em vez de esconder o resultado.

## Evidência real e reprodução

A auditoria da cena licenciada de Tears of Steel está em `docs/evidence/2026-11-13/`. É fala original em inglês, não validação PT-BR/GTA RP. O diagnóstico real sempre mantém o candidato rejeitado fora da produção; os vídeos são marcados NOT APPROVED.

```sh
python -m unittest tests.test_caption_audit -v
python -m nuvem.real_validation --download --framing-mode preserve_two_faces
```

O workflow de mídia real entrega a auditoria em `validation.json` e nas comparações de layout. Sucesso do workflow significa execução do diagnóstico; `caption_audit.passed=false` continua reprovação técnica de legenda. Os testes positivos de orquestração usam doubles explicitamente identificados.
