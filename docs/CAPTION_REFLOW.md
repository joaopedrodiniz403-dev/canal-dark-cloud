# Reagrupar e renderizar legendas com legibilidade

O gate anterior identificou cues rápidas em fala real licenciada. `nuvem.caption_reflow` agora procura uma partição completa das palavras remapeadas, preservando texto, ordem, início e fim. Não corrige o ASR e não estica os tempos para fabricar aprovação.

A programação dinâmica escolhe grupos variáveis próximos de três palavras, com até oito palavras, duração de até quatro segundos, no máximo duas linhas de 32 caracteres e sem unir falas separadas por mais de 1,2 s. Cada grupo precisa satisfazer o mesmo gate: pelo menos 300 ms e no máximo 25 caracteres/s. Esses limites são política inicial explícita, não resultado de pesquisa perceptiva. Se não houver partição válida, retorna NO_READABLE_PLAN e não gera um par de legendas novo.

ASS e SRT derivam do mesmo plano versionado em captions.plan.json; o ASS é efetivamente queimado no vídeo por FFmpeg. Não alteramos apenas a legenda externa. Esta variante usa texto estável por cue, sem destaque animado de palavra ativa, com fonte DejaVu Sans 52, na união dos painéis. O vídeo continua em movimento com o áudio original. Não é geração original nem conteúdo aprovado.

A integração é restrita ao render alternativo de duas faces (`preserve_two_faces`), ainda em PR e desligado por padrão. O render nativo mantém sua legenda de três palavras e pode ser rejeitado pela auditoria. O gate posterior segue obrigatório, junto com seleção >=8, geometria, QA e revisão humana. Não se deve aplicar a composição de conversa indiscriminadamente a gameplay/webcam.

O diagnóstico compara baseline nativo com alternativa de duas faces e novo agrupamento. Fonte, áudio, palavras e remoção de pausas são iguais; os grupos de legendas agora diferem intencionalmente. A medida de crop não mede leitura. Legibilidade perceptiva, contraste, rostos cobertos, erro ASR, entendimento de humor e sincronismo ouvido continuam exigindo revisão. Sem OCR ou avaliação editorial validada.

Evidências reais ficam em docs/evidence/2026-11-14 e nos artifacts do workflow real. O candidato inglês de Tears of Steel continua rejeitado pelo seletor; renders são explicitamente diagnósticos NOT APPROVED. Testes com texto português são contratos de software, não compreensão de fala portuguesa. Ainda falta validar a integração positiva inteira com uma fonte autorizada PT-BR/GTA RP e seleção real >=8.
