# Backend Chopify — integração preparada, validação real pendente

Origem: https://github.com/mehbul/chopify — licença MIT. Revisão fixa: `d576927bf3b764733c97ac1ad324aa9957b0885d`.

O código Python principal, licença, requisitos e referência CLI foram baixados pelo conector GitHub e examinados. `render_clips.py` usa YuNet com fallback Haar para detectar faces em baixa resolução, suaviza a trajetória e aplica o recorte por comandos FFmpeg; permite split screen, ASS/SRT e normalização de áudio. `score_clips.py`, `evidence.py` e `visual.py` combinam candidatos de texto com evidências de áudio e imagem. Isso é mais completo que o primeiro motor, mas não garante uma edição profissional nem boa compreensão de humor em português: várias pistas textuais são inglesas.

O upstream não é um agente aprovador editorial. Sua pontuação recomenda candidatos. Aprovação continua separada e explicitamente falsa no relatório Nuvem Escura.

## Instalar uma única ferramenta

Na raiz do projeto, com Git, Python 3.11+ e FFmpeg/libass instalados:

```sh
git clone https://github.com/mehbul/chopify.git work/chopify
git -C work/chopify checkout d576927bf3b764733c97ac1ad324aa9957b0885d
python -m venv work/chopify-venv
# Linux/macOS; no Windows use work/chopify-venv/Scripts/python.exe
work/chopify-venv/bin/python -m pip install -r work/chopify/requirements.txt
work/chopify-venv/bin/python -m nuvem.chopify_backend --upstream work/chopify
```

Cadastre previamente um arquivo local autorizado em `agent/sources.json`, no formato de [INPUT.md](INPUT.md). O adaptador rejeita fixtures e fontes sem atestado de direitos antes de iniciar o upstream. Confere a revisão e alterações em arquivos rastreados. Não aceita URL de terceiro nem ativa upload.

Ele executa o pipeline real do Chopify: ASR small/CPU, seleção com evidências, 15–59 segundos, até cinco cortes, 9:16, legendas bold de três palavras, remoção de pausas e áudio normalizado. Salva log, MP4/SRT/metadados e relatório de proveniência em `output/chopify`. Uma saída produzida fica `AWAITING_TECHNICAL_AND_EDITORIAL_REVIEW`; retorno zero do processo nunca vira aprovação.

Esta integração é explícita e experimental. Não substitui a produção diária ainda. Falta executar com uma gravação autorizada real, verificar rastreamento no tipo de gameplay, fidelidade das legendas e coerência. Também falta integrar o histórico diário/deduplicação do coordenador a este backend; não usar como operação contínua antes disso.

## Evidência e bloqueios

- Código upstream baixado e analisado; não apenas README.
- Tentativa de executar `--version` localmente falhou por ausência de `cv2`; o upstream importa OpenCV antes mesmo de exibir versão. Portanto não há alegação de execução completa local.
- CI específico instala NumPy/OpenCV e tenta importar o CLI verdadeiro, separado dos testes do adaptador. Isso não valida ASR nem um vídeo final.
- Modelo Whisper e dependências de produção precisam ser instalados/baixados. Nenhuma API paga é necessária para este caminho.
- A amostra colorida anterior era uma fixture interna com tom sonoro. Ela não é uma referência de qualidade e não deve ser oferecida como entrega de Short.
