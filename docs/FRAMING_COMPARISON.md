# Enquadramento de duas pessoas — diagnóstico experimental

O recorte do maior rosto do Chopify pode excluir a outra pessoa durante uma conversa. Esta etapa compara esse recorte com uma composição de dois painéis, usando a mesma cena CC BY de Tears of Steel, áudio, remoção de pausas e transcrição. **Não identifica o falante ativo.** A integração opcional após seleção está descrita em [FRAMING_INTEGRATION.md](FRAMING_INTEGRATION.md); permanece em PR, sem ativação na branch padrão.

## Implementação

`nuvem.framing` detecta todos os rostos em amostras de origem a 4 fps, com o detector já usado pelo backend fixado. As caixas são trazidas às coordenadas da fonte. Só propõe painéis quando há evidência simultânea suficiente de duas faces separadas. Uma pessoa que se move sozinha e uma multidão não são transformadas em dois interlocutores inventados.

Os recortes acompanham a pessoa à esquerda e à direita, com interpolação a 24 fps. Essa associação é **espacial**, não verificação de identidade. As pessoas podem trocar de painel se cruzarem; a abordagem ainda precisa de validação para câmeras, mudanças de plano e gameplay diferentes.

Lacunas pequenas de detecção podem ser interpoladas. Fora dos intervalos de evidência suficiente, o quadro inteiro aparece sobre fundo desfocado, preservando o cenário e os cartões do filme. Falta global de evidência estável produz `NO_SAFE_DUAL_PLAN`, sem render alternativo fabricado. Não há zooms aleatórios ou escolha fictícia de quem está falando.

As legendas da composição dupla ficam na união dos painéis, com palavra ativa destacada. Elas continuam sendo a transcrição ASR não corrigida: a mudança de enquadramento não valida seu texto ou sincronismo perceptivo.

## Medida e limitações

Para cada caixa detectada **na origem**, calcula-se a fração da caixa que o crop mantém. A detecção conta como preservada quando pelo menos 95% da sua área permanece em algum painel. A análise da origem evita considerar sucesso simplesmente porque um detector no vídeo já cortado deixou de enxergar a pessoa excluída.

Resultados locais desta cena:

| Critério | Maior rosto | Dois painéis + quadro inteiro quando incerto |
|---|---:|---:|
| Detecções de rosto preservadas | 63/122 (51,64%) | 122/122 (100%) |
| Amostras com os dois rostos preservados | 2/61 (3,28%) | 61/61 (100%) |
| QA técnico existente | passou | passou |
| Gate geométrico observado (≥95%) | reprovou | passou |
| Aprovação editorial | não | não |

O total é de **observações amostradas**, não pessoas únicas nem garantia sobre todos os frames. Em 23 amostras não houve detecção; elas não viram falso sucesso ou verdade de referência. Caixas detectadas não são ground truth: uma falha do detector pode ocultar um problema. Isso não prova que o vídeo mostra o interlocutor correto, evita todas as obstruções ou tem bom conteúdo.

O caso mediu 84 amostras totais na cena retimada de ~20,88 s. O plano duplo ficou ativo entre 2 e 17,25 s, com painéis de origem 304×270; nos demais momentos o quadro foi preservado. As duas saídas ficaram 1080×1920 e passaram nas oito verificações técnicas de áudio/vídeo existentes. A inspeção de quadros confirmou ambos os atores nos painéis durante a conversa e o cenário inteiro depois.

A validação também conferiu **2.008/2.008 comandos FFmpeg com resposta Success**. Comandos ignorados/inválidos ou ausência de respostas suficientes fazem o diagnóstico falhar; não basta que o encoder tenha retornado zero.

## Reproduzir e inspecionar

Após o diagnóstico real descrito em `REAL_MEDIA_VALIDATION.md`:

```sh
python -m nuvem.framing_comparison --validation work/real-validation --upstream work/chopify --output work/framing-comparison
```

O workflow de diagnóstico existente reproduz a comparação. Artifacts incluem vídeos marcados **NOT APPROVED**, legendas, atribuição CC BY, geometria, caixas, logs de comandos e QA. Não incluem o filme completo nem os modelos. O histórico e o cadastro do canal não são alterados.

É uma prova técnica em uma cena inglesa licenciada. A etapa seguinte é validar em gravação autorizada em português/GTA RP, lidar com cruzamento/oclusão de pessoas e decidir a composição adequada ao gameplay e à webcam. A seleção editorial e as falhas conhecidas de transcrição continuam sem aprovação. Nenhum vídeo foi publicado.
