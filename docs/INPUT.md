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

## Entrada remota privada no ciclo de nuvem

O ciclo Chopify aceita um objeto HTTPS próprio/licenciado por fonte. A URL completa, inclusive sua assinatura temporária, fica exclusivamente em um **Actions Secret** `NUVEM_MEDIA_URL_1` (há cinco slots, de 1 a 5). Não cole a URL no JSON, issue, PR ou conversa. Não é necessário contratar armazenamento: pode usar um objeto já disponível em armazenamento autorizado.

No registro de fonte, mantenha `rights` preenchido e acrescente:

```json
{
  "path": "incoming/minha-gravacao.mp4",
  "rights": {
    "verified": true,
    "kind": "owned",
    "holder": "Titular da gravação",
    "reference": "Identificador de evidência arquivada",
    "verified_by": "Responsável pela conferência",
    "verified_at": "2026-11-07"
  },
  "remote": {
    "url_env": "NUVEM_MEDIA_URL_1",
    "allowed_hosts": ["seu-host-de-armazenamento.com"],
    "sha256": "SUBSTITUA_PELO_SHA256_REAL_DE_64_CARACTERES_HEXADECIMAIS",
    "max_bytes": 524288000
  }
}
```

O exemplo não é um cadastro executável. Calcule o hash do arquivo original (`sha256sum arquivo.mp4` ou `Get-FileHash arquivo.mp4 -Algorithm SHA256`) e informe o hostname exato autorizado. Se o serviço redirecionar a outro hostname, este precisa ser conferido e explicitamente listado. Só HTTPS/443 é aceito; URLs com usuário/senha, fragmentos ou IP literal são rejeitadas. Links de páginas de YouTube/Twitch não são objetos de vídeo e não são aceitos como substitutos de licença.

No GitHub, configure o valor em **Settings → Secrets and variables → Actions → New repository secret**. A URL deve permitir GET direto e continuar válida quando o ciclo executar. O código só valida metadados públicos e usa o secret no processo de ingestão. A publicação de fonte/direitos no manifesto não configura esse secret automaticamente.

O download requer direitos atestados antes de abrir a conexão. Faz streaming com limite de bytes (padrão 500 MiB, teto 2 GiB), timeout de conexão/leitura de 30 s e deadline cooperativo de 15 min. Verifica SHA-256, tamanho declarado quando presente e presença de streams de vídeo/áudio com ffprobe. Só então move o arquivo temporário ao destino. URL, assinatura e corpo de erro remoto não entram no relatório. Erros são códigos fixos; arquivos parciais são removidos.

Se o destino já existir, ele precisa ter o hash esperado: o agente não sobrescreve silenciosamente uma gravação diferente. A allowlist restringe o destino declarado; a política de rede do ambiente continua sendo aplicada. Esta etapa não faz pesquisa, download de lives nem validação jurídica automática.

Sem secret ou objeto autorizado, o ciclo registra falha de entrada e não produz conteúdo. O acesso a armazenamento real e o teste ponta a ponta com fala continuam pendentes. Artefatos de revisão seguem expirando após sete dias; persistência durável do vídeo final ainda não foi implementada.
