# Cadastro de material autorizado

`agent/sources.json`:

```json
{
  "sources": [{
    "path": "minha-gravacao.mp4",
    "rights": {
      "verified": true,
      "kind": "owned",
      "holder": "Nome do titular",
      "reference": "Identificador verificável da licença ou autorização arquivada",
      "verified_by": "Responsável pela conferência",
      "verified_at": "2026-11-06"
    },
    "layout": "contain"
  }]
}
```

Todos os caminhos são relativos a `media/authorized/`. `kind` aceita `owned`, `licensed`, `permission`. O sistema valida o registro fornecido; não confirma juridicamente uma licença. Não cadastre criadores só porque o vídeo é público.

`layout: contain` preserva a cena e preenche o fundo vertical com desfoque. `center` aplica recorte central explícito; não rastreia personagens. Não o use quando cortar informações relevantes.

Para executar sem baixar um modelo, forneça `transcript: "minha-gravacao.words.json"`. Deve ser uma transcrição real conferida, no formato:

```json
{
  "backend": "transcricao_conferida",
  "words": [
    {"text": "Olha", "start": 0.5, "end": 0.8},
    {"text": "isso!", "start": 0.9, "end": 1.3}
  ]
}
```

Exemplo de formato apenas; duas palavras não geram um corte. Os tempos referem-se à fonte inteira, em segundos, crescentes e sem sobreposição. O motor requer palavras com até 20 caracteres para manter legendas legíveis. Palavras fora desse limite devem ser tratadas na transcrição antes de renderizar; não são silenciosamente truncadas.

Comando com diretórios específicos:

```sh
python -m nuvem.engine --manifest agent/sources.json --media-root media/authorized --output output/cuts --state work/state.sqlite --limit 5 --min-score 55 --model small
```

Pontuação mede pistas textuais, ritmo e fechamento aparente. Não reconhece sarcasmo, punchlines visuais ou contexto completo. Valores de originalidade, interesse e histórico permanecem desconhecidos. Revisão humana deve verificar coerência, legenda versus áudio, crop, título, direitos e políticas; sucesso técnico nunca representa aprovação editorial.
