# Nuvem Escura AI — instruções do agente em nuvem

Leia `docs/CLOUD_AGENT.md`, `docs/VALIDATION.md`, `docs/CHOPIFY.md` e o estado atual do repositório antes de agir. Preserve alterações humanas e use evidência atual do GitHub. O usuário autorizou baixar os projetos relevantes, criar o agente em nuvem e prosseguir no desenvolvimento e correção deste sistema.

## Objetivo e execução

Construa e opere uma fábrica de até cinco Shorts de qualidade por dia. Continue a implementação por etapas, com código, testes e evidências. Use projetos existentes quando reduzirem complexidade. Não confunda criar uma automação com concluir o produto.

1. Audite dependências e licenças nos snapshots de `agent/upstreams.lock.json`; não instale todos indiscriminadamente.
2. Priorize validar o pipeline real Chopify com fonte autorizada e fala real, medindo legibilidade, crop, contexto e áudio. Corrija falhas; não exiba fixtures sintéticas como entregas.
3. Implemente pesquisa de tendências com fontes e datas verificáveis, sem inferir direito de reutilização a partir de acesso público.
4. Desenvolva originais com roteiro próprio, cenas em movimento e TTS neural local licenciado; nunca eSpeak, slides com parágrafos ou falsa geração de vídeo.
5. Integre ranking explicável, contexto narrativo, QA técnico e editorial, correção e fila de aprovação.
6. Prepare YouTube API oficial, OAuth seguro, upload privado, aprovação humana e agendamento. Colete métricas reais somente quando houver acesso.
7. Mantenha memória em arquivos versionados, histórico de produção e relatórios verificáveis. Não dependa exclusivamente de arquivos temporários ou cache do runner.

## Limites obrigatórios

- Priorize ferramentas gratuitas. Não contrate nuvem, não use APIs pagas/Runway/fal/ElevenLabs nem créditos pagos sem autorização específica.
- Nunca publique publicamente no YouTube sem aprovação explícita para essa funcionalidade. Aprovar tecnicamente um MP4 não aprova conteúdo nem publicação.
- Só processe material próprio, licenciado ou com permissão verificada. Nunca baixe/republique lives dos criadores indicados sem evidência de autorização.
- Use os conectores/credenciais autorizados normalmente; não leia nem imprima valores de segredos. Segredos não entram no repositório ou artifacts.
- Respeite política de rede. Se o proxy estiver indisponível, use conector GitHub ou Actions; não contorne a rede.
- Faça alterações em branch/PR com testes pertinentes. Integrações pendentes permanecem explicitamente pendentes. Não altere outras automações do usuário.
- Sem mídia ou acesso, registre o bloqueio concreto e continue tarefas independentes. Não transforme ausência de conteúdo em demonstração sintética.
- Relatórios devem dizer o que foi executado, artefatos, resultados medidos e próximo bloqueio; nunca invente métricas, testes ou qualidade profissional.
