# Legendas legíveis no retrato nativo

O diagnóstico português mostrou que trocar grupos de palavras não bastava: o planejador não usava a tolerância de exibição já permitida pela auditoria. Agora a programação dinâmica considera o fim da cue anterior e pode antecipar/permanecer até 150 ms em relação à primeira/última palavra. Os timestamps e o texto das palavras, o áudio e a seleção não são reescritos.

A exibição fica numa grade de centésimos de segundo comum a ASS e SRT, nunca sobreposta ou fora do vídeo, mantendo 300 ms mínimos, 25 caracteres/s máximos, duas linhas de 32 caracteres no planejador, até oito palavras e quatro segundos por grupo. A preferência por grupos próximos de três palavras penaliza também deslocamento da exibição. Sem solução, continua NO_READABLE_PLAN; não baixa limites para aprovar.

A auditoria de SRT agora calcula duração e velocidade em milissegundos inteiros, evitando falsa reprovação de exatamente 25 caracteres/s ou 300 ms por erro de ponto flutuante. Um intervalo 1 ms menor que o permitido continua reprovado. A quantização para centésimos e a comparação de 150 ms usam Decimal: 18,58 s não podem perder um tick por representação binária. O limite não foi aumentado.

## Renderização e integração

`nuvem.readable_portrait` usa o renderer do checkout Chopify verificado, com os mesmos recorte/tracking, remoção de pausas e normalização. Adaptadores em memória trocam somente a produção de ASS/SRT durante essa chamada serializada e restauram as funções mesmo em erro. Arquivos rastreados do upstream não são modificados. O plano e os hashes do ASS efetivamente entregue ao FFmpeg e do SRT exportado ficam em captions.plan.json e caption-render.json. Uma divergência do conjunto de palavras/intervalo na exportação interrompe o render.

O modo opcional por fonte `caption_mode: "readable"` é aplicado após seleção nativa e checagem de origem/intervalo/nota >=8. As exportações nativas permanecem intactas; somente a alternativa que passa no QA é devolvida, e a auditoria final continua obrigatória. Falhas de execução propagam erro. Candidatos rejeitados ou ausência de saídas não ativam esse render. Modos padrão não foram ativados/modificados na main.

O diagnóstico português também pode comparar a alternativa em candidato já rejeitado, exclusivamente para medir o renderer. Isso não atravessa seleção, ciclo, histórico de revisão ou publicação. Os vídeos ficam NOT APPROVED, com créditos e CC BY-SA 4.0. Cada variante exige revisão humana própria dos bytes finais.

## Evidência real no ambiente herdado

Mesma entrevista licenciada e candidato local (nota 4,35, fora da fila): 153 palavras ASR no trecho de entrada. No render diagnóstico, a legenda nativa teve 21 cues e pico 43,75 caracteres/s; a alternativa ficou em 15 cues, pico 25,0 e passou na auditoria. Lead/lag máximos 100 ms. Ambas passaram nas oito verificações técnicas, com duração 16,683 s.

O hash do áudio decodificado em PCM mono 48 kHz s16le foi igual entre as variantes, pelo método registrado no JSON. Inspecionado um quadro a 8 s: rosto e crédito preservados, legenda legível sem cobrir o rosto naquele quadro. Isso não comprova sincronismo percebido em todo o vídeo nem fidelidade ASR, contexto ou qualidade editorial.

Dados/hashes em docs/evidence/2026-11-18/. Resultados Actions podem variar por ASR e ficam separados no PR. Não há WER sem referência independente conferida por escuta. Gameplay/GTA RP, revisão editorial por IA e aprovação humana de conteúdo real continuam pendentes. O cadastro do canal permanece vazio; nada foi publicado.
