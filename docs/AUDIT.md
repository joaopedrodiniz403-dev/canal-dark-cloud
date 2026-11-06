# Auditoria — 6 de novembro de 2026

Base examinada: `e58541f69d6777f0690e18a45d1f75877a21e8f8` de `joaopedrodiniz403-dev/canal-dark-cloud`. Leitura via conector oficial GitHub; clone HTTP no terminal falhou por proxy indisponível. Não foram lidos segredos.

## Achados no projeto

| Componente | Evidência | Decisão |
|---|---|---|
| `main.py` | PNGs estáticos + eSpeak, três cenas, aprovação apenas por duração/resolução/tamanho | Substituir entrada por motor de cortes |
| `agent/produce.py` | `render_original` usa imagens estáticas; `render_clip` só recorta centro; sem transcrição/legendas | Substituir e remover fallback de slides |
| `agent/score.py` | Pontua comprimento do texto e quantidade de cenas; não analisa reação ou vídeo | Não usar para cortes; heurística separada com limitações explícitas |
| `agent/authorized_clips.json` | Lista vazia | Sem material real para teste editorial |
| `agent.yml` | Agenda diária, eSpeak, nenhuma persistência de deduplicação | Reutilizar orquestração/artifacts; trocar motor, adicionar histórico |
| `generate.yml` | Apenas gera outro slide, sem testes | Transformar em CI de regressão e render real |
| `download-tools.yml` | Clona quatro projetos, sem integrar nem avaliar | Preservado manual, não executado nesta entrega |

Não havia testes, tracking facial, busca de tendências, métrica real, upload YouTube ou evidência de direitos de streamers.

## Projetos avaliados

Metadados, árvores e arquivos de código/dependências consultados via API GitHub. Datas abaixo são `pushed_at`, indicam atividade e não garantem manutenção ou estabilidade. Não instalamos os quatro aplicativos completos. Não houve cópia de código deles.

| Projeto / revisão inspecionada | Licença informada | Código/dependências e hardware | Avaliação |
|---|---|---|---|
| [OpenShorts](https://github.com/ws-tyd/openshorts) `0240abe` | MIT; push 09/10/2026 | `requirements.txt`: Torch/Torchvision, Ultralytics, TransNetV2, MediaPipe, faster-whisper, Gemini, FastAPI; `clip_selection.py` contém seleção Gemini e preços | Integração abrangente, mas stack pesada e chamadas externas. GPU ajuda em visão/ASR. Não incorporar o conjunto para um runner gratuito; licenças de modelos/Ultralytics exigem análise própria além da licença do repo |
| [AI YouTube Shorts Generator](https://github.com/Anil-matcha/AI-Youtube-Shorts-Generator) `13451d4` | MIT; push 06/11/2026 | `requirements-local.txt`: faster-whisper, OpenCV, OpenAI/Google SDKs; `shorts_generator/local/clipper.py` percorre frames com Haar, suaviza centro, grava temporário e remuxa áudio | Modo local CPU viável, mas detecção da maior face não identifica falante nem garante GTA RP. Reutilizar os componentes base, sem adotar a aplicação completa |
| [NovaClip](https://github.com/samolubukun/NovaClip) `70e561e` | MIT; push 01/09/2026 | Worker Rust + frontend; `transcribe.rs` tem Vosk e interfaces Deepgram; `crop.rs` só converte proporções e delega crop; árvore inclui reframe Python e pesos YOLO | Mais infraestrutura e modelos que o necessário nesta fase. Não inferir tracking completo a partir de `crop.rs`; pipeline completo não executado |
| [Chopify](https://github.com/mehbul/chopify) `d576927` | MIT; push 06/11/2026 | `requirements.txt`: yt-dlp, faster-whisper, OpenCV, NumPy; `score_clips.py` usa pistas lexicais, finais de frase e reranking opcional Ollama | Melhor proximidade técnica para CPU/local. Heurísticas majoritariamente inglesas no arquivo consultado; adotar abordagem de componentes pequenos em português. Ollama/7B exigiria RAM adicional e validação de modelo |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | MIT; push 02/11/2026 | CTranslate2, CPU int8 ou GPU; modelo exige download, RAM/tempo dependem da variante | Escolhido como ASR opcional. Pacote/modelo não disponíveis no ambiente de teste sem rede; integração escrita, execução ASR pendente |
| [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) | BSD-3-Clause; push 02/11/2026 | CPU/OpenCV; mudanças de cena não identificam sozinhas humor ou narrativa | Adiar para avaliação multimodal e cortes por cena |
| [Auto-Editor](https://github.com/WyattBlue/auto-editor) | Unlicense; push 06/11/2026 | Edição baseada em níveis/atividade, executável e runtime próprios | Não adicionar outra timeline; cortes conservadores por gaps de palavras nesta fase |
| FFmpeg | LGPL/GPL conforme build | Build local 7.1.5 com libx264/libass e `--enable-gpl`; CPU, sem GPU obrigatória | Escolhido para edição, áudio, legendas e inspeção. Distribuir binários requer conferir obrigações da build |
| [Piper](https://github.com/OHF-Voice/piper1-gpl) | GPL-3.0; push 02/11/2026 | TTS neural local CPU; licença de cada voz é independente | Alternativa gratuita para fase de originais. Não instalado, não gera voz nesta entrega; validar português e autorização da voz |
| OpenCV Haar / MediaPipe / YOLO | Licenças variam por pacote/modelo | Haar é leve em CPU, limitado a rostos frontais; tracking requer associação temporal. MediaPipe adiciona dependências; YOLO exige revisar licença/pesos | Não declarar enquadramento inteligente pronto; layout preserva a fonte inteira. Tracking futuro precisa testes com webcam pequena, HUD e múltiplos rostos |

Licenças dos repositórios não autorizam reutilização dos vídeos, vozes, músicas nem pesos. Não selecionamos vídeos de streamers sem permissão verificada.

## Escolha desta entrega

Python stdlib + FFmpeg/libass + faster-whisper opcional. Sem API paga, LLM obrigatório, GPU ou instalação indiscriminada. Isso entrega uma base executável e auditável, com seleção heurística e revisão humana, mas não resolve compreensão semântica profissional. A comparação com referências de grandes canais depende de material autorizado e avaliação editorial real.
