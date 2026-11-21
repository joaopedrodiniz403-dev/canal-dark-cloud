# Comparação real de modelos ASR

O comparador executa `small` e `medium` em **CPU/int8, quatro threads**, sequencialmente e em processos separados, sobre os mesmos bytes da cena licenciada de Tears of Steel. Usa a mesma chamada de transcrição da revisão Chopify fixada. A legenda de referência só é usada depois da transcrição para medir divergência; não é enviada como prompt, dica ou correção ao modelo.

## Resultado observado em 10/11/2026

| Modelo | Erros / referência normalizada | WER | Tempo de transcrição observado |
|---|---:|---:|---:|
| small | 12 / 75 | 16% | 9,328 s |
| medium | 10 / 75 | 13,33% | 34,758 s |

Redução: **2,67 pontos percentuais**, com **3,726×** o tempo de inferência nesta execução. Outra passagem preliminar mediu ~8,3 s e ~22,5 s: os tempos variam com carga e cache do ambiente compartilhado e não são SLA. O tempo de carregamento/download é registrado separadamente e não entra nessa razão. Os relatórios preservam as transcrições, timestamps, hashes da entrada/referência e parâmetros de execução.

O ganho nesta cena é modesto e ainda deixa erros importantes, como a expressão sobre as garras robóticas. Isso não comprova qualidade profissional, generalização para português ou GTA RP. **Não mudamos o padrão `small`, o mínimo editorial de 8/10 nem a exigência de revisão humana.** A identificação do falante ativo continua sem solução validada.

## Configuração explícita

Uma fonte em `agent/sources.json` pode incluir `"asr_model": "medium"` ao lado de `path` e `rights`. Sem esse campo, continua `small`. Só esses dois nomes são permitidos; URLs, caminhos de modelo e flags arbitrárias são rejeitados antes de iniciar o backend. O relatório `upstream_report.json` registra o modelo selecionado.

`medium` exige mais download/RAM/CPU e pode ser inadequado para lives extensas no limite de 55 minutos do runner. Esta comparação curta não certifica o processamento de uma live longa. Não é uma ativação de API paga ou GPU.

## Reproduzir

Com o backend fixado e dependências de `requirements-cuts.txt` aplicadas:

```sh
HF_HOME="$PWD/work/hf-cache" python -m nuvem.asr_benchmark --download
```

A origem e o SHA-256 do filme são fixos, conforme `REAL_MEDIA_VALIDATION.md`. O comparador só transcreve, mede e salva JSON/logs; não gera vídeo para o canal, não altera fontes/estado, não publica e não concede direitos de reutilização a outras mídias. Os artifacts incluem atribuição CC BY, sem distribuir o filme ou os modelos.

O workflow `asr-comparison.yml` executa em PR/manual, **sem agenda diária** e com permissão apenas de leitura. Arquivos de diagnóstico expiram após 14 dias. O workflow de render real também aceita `asr_model` na execução manual; isso não altera a produção.

Uma comparação incompleta, com entradas/referências/configurações diferentes ou medidas inválidas não pode recomendar um modelo. A decisão sobre padrão de produção permanece fora do benchmark. É necessária validação em gravação autorizada em português e avaliação humana da fidelidade/contexto das legendas.
