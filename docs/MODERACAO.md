# Moderação — RNQ-tecelagem.xlsx

Tudo que as pessoas enviam pelo site chega nesta planilha (via `atualizar.py` ou `sincronizar.py`).
O sincronizador **só acrescenta linhas novas** (pelo ID do envio) e nunca altera o que você editou.

Cores: **amarelo** = você edita · **vermelho** = privado, nunca publicado · **cinza** = interno, nunca publicado.

## Rotina sugerida (15 minutos por semana)

1. `python3 atualizar.py` (ou "atualiza o mapa" para o Claude).
2. Abra `painel/painel-tecelagem.html` → seção **Esperando você**.
3. Modere na planilha, salve, rode de novo.
4. Faça 2 ou 3 **apresentações sugeridas** do painel e registre em **Apresentações**.

## Abas

| Aba | Chega do formulário | O que você faz | O que vai para o site |
|---|---|---|---|
| **Mural** | "Publicar oferta ou pedido" | `Publicar? = Sim` para publicar. Ajuste título/áreas se precisar. `Status = Atendido` quando resolver | Tipo, título, descrição, áreas, nome, data, status |
| **Respostas do mural** | "Posso ajudar" / "Tenho interesse" | Apresente as pessoas (contato das duas está aqui e na aba Mural) e marque `Apresentação feita? = Sim`. Registre em **Apresentações** | Nada |
| **Perfis** | "Atualizar meu perfil" | Confira se é a pessoa mesmo (contato ajuda). `Publicar? = Sim` | Posso compartilhar, quero aprender, toparia convocar. "Colaboro com" vira ligação. "Gostaria de colaborar com" **não** é publicado — alimenta as sugestões do painel |
| **Ligações sugeridas** | "Eu conheço essa pessoa" | `Aprovar? = Sim` cria a ligação (RF6) | A ligação |
| **Saídas** | "Quero sair do mapa" | Já entra com `Remover? = Sim` (RF8). Só troque para `Não` em caso de abuso evidente (ex.: alguém pedindo saída de outra pessoa) | Remove pessoa, ligações, itens do mural e iniciativas propostas por ela |
| **Confirmações** | "Quero ficar no mapa" | Nada — é só registro de consentimento | Nada |
| **Iniciativas** | "Propor iniciativa" | Confirme com os participantes citados. `Publicar? = Sim`. `Status = Concluída` quando acabar | Tipo, título, descrição, áreas, participantes **que estão no mapa**, "precisa de", quem propôs |
| **Participações** | "Quero participar" | Encaminhe para quem propôs e marque `Encaminhado? = Sim` | Nada |
| **Cadastros** | "Faça parte" (participar.html) | Confira os dados e, se a pessoa escolheu aparecer no mapa e confirmou 18+, marque `Incluir no mapa? = Sim`. Tema ou comunidade nova sugerida chega nas colunas cinza: se fizer sentido, crie em `rnq/config.py` (com o nome em inglês) e corrija a linha. Oferta e pedido autorizados já chegam também na aba **Mural**, esperando `Publicar?` | Nome, cargo, organização, LinkedIn, propósito, temas, comunidades, atuação, fios e ofertas. **Nunca**: contato, cidade, aniversário, organizações de interesse, necessidade, objetivo, formatos e indicações (ficam só na planilha). Se a pessoa já estava no mapa, o cadastro soma ao que ela já tinha |
| **Apresentações** | — (você preenche) | Seu diário de tecelagem. `Apresentadas`, `Acompanhando` ou `Colaborando` = as duas pessoas aparecem ligadas no mapa | A ligação |
| **Papéis** | — (você preenche) | Selos de papel na rede. **Só com o OK da pessoa** | O selo no card |
| **Correções** | — (você preenche) | Corrige nome, cargo, organização ou LinkedIn sem mexer na planilha de seleção. `Aplicar? = Sim` | O valor corrigido |

## Regras de escrita

- **Áreas** (mural e iniciativas): separe por `;` e use nomes de temas ou comunidades do mapa.
  Nome desconhecido é ignorado e aparece em AVISO.
- **Nomes de pessoas** (participantes, colaboro com, apresentações): como aparecem no mapa. Acentos e
  maiúsculas não importam. Nome que não está no mapa vira AVISO e não é exibido.
- **Contatos colados em texto público** são removidos automaticamente, com AVISO.

## Papéis (Network Weaver Handbook)

| Papel | Quem é |
|---|---|
| Conector(a) | Apresenta pessoas que ainda não se conhecem e acompanha até a conexão virar relação |
| Coordenador(a) de projetos | Ajuda grupos a transformar conversa em projeto colaborativo |
| Facilitador(a) | Cuida de encontros e processos para que todo mundo participe |
| Guardiã(o) da rede | Cuida da infraestrutura da rede: comunicação, acordos, ferramentas |

Dar papéis a outras pessoas é o caminho para a rede deixar de depender de você (sair da fase hub-and-spoke).
