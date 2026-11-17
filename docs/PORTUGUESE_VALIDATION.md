# Diagnóstico reproduzível com entrevista real em português

`nuvem.portuguese_validation` executa o backend fixado em fala portuguesa real. A fonte é Entrevista com Murilo Sá Toledo, gravação/pós-produção de Rodrigo Tetsuo Argenton e reportagem de Érica Azzellini, publicada no Wikimedia Commons como obra própria em CC BY-SA 4.0. Página conferida na revisão 1121577018:

https://commons.wikimedia.org/w/index.php?title=File:Entrevista_com_Murilo_S%C3%A1_Toledo.webm&oldid=1121577018

Foi conferida a licença publicada, a declaração de origem própria e o hash do arquivo; não inferimos direitos por simples disponibilidade pública. O SHA-1 baixado coincide com o publicado: 887d08c0090a689735a1be49e9e425a152753c06. SHA-256 fixado: 96e790b029224ffafd2d4e7d740435104a04b580109d97ee9bcf3d5af1e88021. O download tem limite de 60 MiB; cache incorreto e hash divergente são rejeitados.

A atribuição completa, fonte, licença e modificações acompanham o MP4 e sidecars. **Os derivados audiovisuais deste diagnóstico são distribuídos em CC BY-SA 4.0**, preservando a exigência de compartilhamento pela mesma licença. Isso se aplica aos derivados da mídia, não altera a licença do código independente. Não há endosso dos autores ao canal.

## Execução e escopo

```sh
python -m nuvem.portuguese_validation --download --upstream work/chopify
```

O intervalo fixo 30–75 s é extraído do original verificado; Chopify executa ASR small/CPU, seleção >=8, evidências de áudio/imagem e formato nativo. O idioma detectado deve ser pt. Nenhuma transcrição fornecida ou nota fabricada substitui esse caminho. Não modifica agent/sources.json, estado de produção, decisões ou YouTube.

O primeiro candidato real pode ser renderizado exclusivamente como diagnóstico, mesmo se rejeitado pela seleção. É marcado NOT APPROVED, creditado e explicitamente inelegível para produção. Sua nota e intervalo originais são preservados. Sem candidato, não inventamos um segmento de substituição. A saída mede QA técnico, timestamps, tracking e exportação das legendas. O planejamento de agrupamento é medido separadamente; ausência de solução permanece reprovação.

Não há transcrição independente conferida por escuta: WER fica null, accuracy_verified=false e human_listening_review_required=true. Comparar SRT ao ASR só verifica integridade de exportação. Contagem de detecções faciais não identifica o interlocutor nem prova qualidade do crop.

## Evidência local de 17/11

- Português detectado, 153 palavras ASR.
- Dois candidatos, máximo 4,35/10; zero saídas automáticas.
- Render diagnóstico: 16,683 s, oito verificações técnicas aprovadas; RMS -13,77 dBFS e fração de amostras clipadas 0,000839.
- Tracking: 82/83 amostras com detecção, sem ground truth. Em um quadro a 8 s, o entrevistado e os créditos ficaram visíveis; não é verificação de todo o vídeo.
- Oito de 21 cues excederam 25 caracteres/s; pico 43,75. Texto exportado coincide com o ASR, cuja acurácia não foi validada.
- O planejador atual não encontrou uma partição legível para esse candidato. Não foi gerado vídeo alternativo para simular correção.

Evidências em docs/evidence/2026-11-17/. Os números da nuvem ficam separados na descrição do PR porque ASR/tempos podem variar. O workflow real entrega MP4 marcado, atribuição CC BY-SA, SRT, transcrição, seleção, tracking e auditoria; não distribui o original completo ou modelos.

É uma entrevista cultural, não gameplay/GTA RP nem avaliação editorial profissional. Permanecem necessárias revisão humana da fala/contexto e validação no cenário-alvo. A pontuação heurística não é um avaliador editorial por IA validado. Cadastro e fila do canal continuam sem entradas novas.
