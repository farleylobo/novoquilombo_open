# SPEC-RNQ-003 · Painel admin com login

**Status:** As fases F0 a F2 estão implementadas (versão 2.6.0, 15/10/2026), com testes. A F3 fica para depois.
O painel já está no ar em modo demonstração. Os dados reais entram quando o Farley rodar `painel_admin.py configurar`.
**Depende de:** SPEC-RNQ-001 (visão pública) e SPEC-RNQ-002 (tecelagem e painel do tecelão).
**Guia de uso:** `docs/PAINEL-ADMIN.md`.

## Problema

O painel do tecelão é um HTML local, gerado no Mac do Farley. Isso causa dois problemas:

- Só o Farley vê a saúde da rede e as apresentações sugeridas, e a rede continua dependendo de um hub.
- A moderação fica presa numa planilha local.

## Objetivo

1. A equipe vê o painel do tecelão, e cada pessoa vê só as comunidades que tece.
2. A moderação acontece no painel, que passa a ser a fonte da verdade.
3. Os contatos privados ficam protegidos por login forte e nunca chegam ao site público.

## Decisões (Farley, 15/10)

| # | Tema | Escolha |
|---|---|---|
| D1 | Papéis | Admin vê a rede toda. Tecelão vê só as suas comunidades. Moderador fica para depois |
| D2 | Onde vive | App novo e aberto (`admin/` no `novoquilombo_open`), num site separado no Netlify. A Átria se diferencia por hospedagem gerenciada, várias redes, IA e customização |
| D3 | Dados de leitura | Visão gerada pelo pipeline do Mac, uma por escopo: rede toda e cada comunidade |
| D4/D5 | Escopo | Leitura e aprovações. **O painel é a fonte da moderação** |
| D6 | Stack | Supabase, região São Paulo (Auth, Postgres e RLS), mais uma Edge Function para convites |
| D7 | Idiomas | PT e EN desde o início |
| D8 | Primeira equipe | Só o Farley. A entrada da June está em standby |
| D9 | Quem aprova | Tecelão aprova os itens das suas comunidades. Admin aprova tudo |
| D10 | Autonomia | Admins gerem a equipe pelo próprio painel |

## Como foi construído

- **App:** página estática sem build (HTML, CSS e JS puro), com `vendor/supabase.js` e fontes servidas pelo próprio site, sem CDN.
  - **Login:** código de 6 dígitos ou botão por e-mail, sempre com `shouldCreateUser: false`.
  - **MFA:** cadastro com QR code e desafio, exigidos para admin.
  - **Telas:** Visão da rede, Moderação, Equipe e Histórico.
  - **Demonstração:** usa a rede fictícia e tem a opção "ver como".
- **Visão da rede:** é o painel do tecelão (`rnq/painel.py`, `modo='painel'`), gerado em PT e EN para cada escopo.
  - Roda num iframe `sandbox="allow-scripts"`, sem acesso à sessão.
  - Copiar e ajustar a altura passam por `postMessage`, sempre conferindo a origem.
- **Banco (`admin/supabase/schema.sql`):**
  - **Tabelas:** `equipe`, `comunidades`, `equipe_comunidades`, `snapshots`, `moderacao` e `auditoria`.
  - **Acesso:** RLS em tudo. O navegador não escreve direto em nenhuma tabela.
  - **Funções `rnq_*`:** `rnq_decidir`, `rnq_equipe_*`, `rnq_meu_perfil` e `rnq_definir_idioma`. As `rnq_pipeline_*` só aceitam a chave secreta.
  - **Travas:** auditoria imutável e pelo menos um admin ativo.
- **Pipeline:**
  - `exportar.executar(decisoes=...)` aplica as decisões do painel antes de montar o site.
  - `rnq/admin.py` monta os itens de moderação, o recorte por comunidade e as visões.
  - `atualizar.py` busca as decisões e depois sincroniza.
  - Itens novos entram com a decisão que a planilha já tinha (migração única). Itens que somem da planilha são apagados.
- **Convites:** a Edge Function `convidar` primeiro confere `rnq_eh_admin` com o login da própria pessoa e só então convida com a chave de serviço.
- **Configuração:** `painel_admin.py configurar` usa a Management API para aplicar o schema, configurar o Auth e os e-mails PT/EN, publicar a função, gravar as chaves e criar o primeiro admin.

## Regras funcionais (somam-se às RF1–RF19)

| # | Regra | Onde é garantida |
|---|---|---|
| RF20 | Só entra quem foi convidado. Admin usa MFA (aal2) | Auth (`disable_signup`), `shouldCreateUser: false`, RLS com `aal2` |
| RF21 | Tecelão só vê e decide o que é das suas comunidades | RLS e visões montadas por comunidade (`recortar`) |
| RF22 | A decisão do painel substitui as colunas da planilha | `aplicar_decisoes`, com aviso quando a planilha discorda |
| RF23 | Toda decisão e toda mudança na equipe vão para a auditoria, que é imutável | funções `rnq_*` e gatilho `auditoria_imutavel` |
| RF24 | A chave secreta nunca entra no app | `painel_admin.publicar` e `tests/test_admin.py` |
| RF25 | Quem saiu do mapa some do painel, inclusive os contatos | `sem_saidas` + sincronização |
| RF26 | Cadastro de quem escolheu não aparecer ou não confirmou 18+ não é aprovado | `bloqueio` no item + `rnq_decidir` |
| RF27 | Só admin convida ou muda papel, comunidades e acesso | `rnq_equipe_atualizar` e Edge Function |
| RF28 | O último admin ativo não sai | gatilho `equipe_ultimo_admin` |
| RF29 | Tirar o acesso corta na hora | RLS (`ativo`) e remoção das sessões |

## Critérios de aceite e testes

| CA | Teste |
|---|---|
| CA20 · tecelão de A não lê B | `tests/sql/rls.test.mjs`, `tests/test_admin.py` (RecortePorComunidade), e2e "ver como tecelã" |
| CA21/CA22 · aprovado vai ao site, recusado não | `tests/test_admin.py` (Decisoes) |
| CA23 · sem convite, sem conta | RLS (`fora`), e2e "não foi convidado" |
| CA24 · mesmos números do painel local | a visão é gerada pelo mesmo `painel.gerar` |
| CA25 · nenhum contato no JSON público | validação RF12 de sempre + `Decisoes.test_site_obedece_ao_painel` |
| CA26 · admin gere a equipe sozinho | e2e "equipe" e "tirar o acesso", RLS |
| CA27 · tecelão não muda o próprio papel | `tests/sql/rls.test.mjs` |
| CA28 · último admin | `tests/sql/rls.test.mjs`, e2e |

## Fases

| Fase | Situação |
|---|---|
| F0 · Base (banco, login, MFA, Equipe) | Pronta. Falta o Farley rodar `configurar` |
| F1 · Leitura (visões PT/EN por escopo) | Pronta |
| F2 · Moderação no painel | Pronta |
| F3 · Tempo real (site lendo do banco, formulários direto no Supabase, papel de moderador) | Para depois |

Até a F3, uma aprovação chega ao site público quando o Farley roda `atualizar.py` + `publicar.py`.

## Segurança e LGPD

Os detalhes estão em `docs/PAINEL-ADMIN.md`. Em resumo:

- **Base legal:** legítimo interesse.
- **Aviso de privacidade:** precisa mencionar o Supabase em São Paulo.
- **Tecelões fora do Brasil:** validar o art. 33 da LGPD antes de convidar.
- **A verificar:** o DPA do Supabase e onde ficam os backups.
- **Retenção:** itens recusados ficam no painel, com o motivo, enquanto a linha existir na planilha. Apagar a linha, ou um pedido de saída, apaga o item. A auditoria guarda só ids, títulos e decisões.

## Em aberto

1. **E-mail próprio (SMTP)** para convidar outras pessoas: o padrão do Supabase só entrega para a equipe do projeto e envia 2 e-mails por hora.
2. **Ativar o fluxo "manter ativo"** (segredos no GitHub) ou migrar para um plano pago quando houver uso real.
3. **F3:** formulários gravando direto no Supabase e site lendo os itens aprovados.
4. **June (standby):** e-mail, MFA e LGPD.
