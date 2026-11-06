# Evidências e estado da entrega

## Execução local

Ambiente Linux, Python 3.11+, FFmpeg 7.1.5 com libass/libx264. Acesso do terminal à rede indisponível por conexão recusada ao proxy; GitHub acessível pelo conector. Nenhum serviço pago utilizado.

`python -m unittest discover -v`: testes de direitos, traversal/symlink, timestamps inválidos, candidatos completos, remapeamento de pausas, escaping ASS, sobreposição, fila vazia, renderização 1080×1920, áudio silencioso rejeitado e deduplicação SQLite. O teste integrado realmente invoca FFmpeg e decodifica o resultado.

`python -m tests.demo`: gera 18 segundos de padrão de vídeo em movimento e tom de 440 Hz, com transcrição **sintética**, renderiza o trecho escolhido e salva evidências em `output/demo`. Identificação obrigatória: `TECHNICAL_TEST_ONLY`. Não é amostra editorial nem teste de compreensão de fala.

## O que as evidências não comprovam

- Não há gravação de entretenimento autorizada no cadastro original. Não foi realizado teste editorial real nem comparação profissional.
- faster-whisper não está instalado e o modelo não foi baixado no ambiente local. O caminho ASR está implementado, mas não foi executado. É possível rodar com transcrição word-level real previamente verificada.
- Layout de cena completa e crop central estão implementados; reconhecimento de personagem, tracking facial, zoom contextual e transições semânticas não estão.
- A heurística analisa texto e ritmo; QA avalia áudio/vídeo depois da montagem. Não é seleção multimodal inteligente de humor/reação.
- Legendas têm timestamps reais quando a entrada tem; QA só verifica limites, não confirma a fidelidade da fala nem percepção de sincronismo.
- Cache do Actions não é armazenamento durável. Não há ingestão privada de mídia em nuvem nesta fase.
- Não há gerador original, pesquisa diária de tendências, API YouTube, agendamento de publicação nem coleta de métricas.

## Estado por fase

1. Auditoria: código atual e principais projetos examinados; nenhum pacote grande instalado sem necessidade.
2. Cortes: primeira implementação e teste técnico real entregues. Aceitação editorial pendente de material autorizado com fala e ASR executado.
3–5. Originais, coordenação avançada e YouTube: pendentes; nenhum comportamento simulado como pronto.
6. Testes: regressão técnica executada; testes reais de conteúdo e comparação com referências pendentes.

Antes de chamar a operação de profissional, medir transcrição, retenção de contexto, recorte, legibilidade e qualidade de áudio em vídeos reais, revisar direitos e publicar apenas após aprovação do titular do canal. Esta entrega não conclui os critérios de aceitação do sistema completo.

## Resultado registrado nesta sessão

- 9 testes passaram em 20,722 s na última execução.
- Demo: 1080×1920, 30 fps, 16,4 s, RMS -15,3 dBFS, fração de amostras clipadas 0; oito verificações técnicas aprovadas.
- Nove grupos de legendas; frame com palavra destacada inspecionado visualmente.
- CLI com cadastro vazio executou e registrou `EMPTY_QUEUE` sem erro.
- Hash SHA-256 do MP4: `69d5d7a4955513ee1eef77d2bb9339485eb78e74b3829b3ca785dc058ae1c4db`.

## Correção após inspeção da amostra entregue

A amostra sintética anterior não atende à aceitação editorial e não deveria ter sido oferecida como resultado para o canal. Seu `quality.passed` se referia exclusivamente aos testes técnicos. Não havia agente autônomo avaliando narrativa ou entretenimento.

O fluxo foi corrigido: produção rejeita fontes marcadas como teste e transcrições com backend sintético; teste interno requer opt-in de código, não recebe pontuação editorial e não gera `REVIEW_REQUIRED`. QA explicita escopo técnico, aprovação editorial falsa e aprovação de publicação falsa. O CI não publica mais essa fixture como artifact de Short.

Após a correção, 13 testes passaram em 21,723 s, incluindo rejeição de fixtures antes de chamar o backend upstream. O backend Chopify foi preparado e sua documentação está em `CHOPIFY.md`; ainda não foi validado ponta a ponta com conteúdo autorizado real. A tentativa local de importar o CLI upstream falhou por falta de OpenCV; o novo job CI testa especificamente essa importação após instalar dependências.
