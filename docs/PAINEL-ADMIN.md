# Painel admin com login

O painel admin é o lugar onde a equipe de tecelagem trabalha. Ele mostra o que aparecia no painel do tecelão (o HTML local) e acrescenta a moderação e a gestão da equipe. Funciona no computador e no celular, e quem entra vê só o que pode ver.

- **Endereço:** https://painel-novoquilombo.netlify.app
- **Demonstração (rede fictícia, sem login):** https://painel-novoquilombo.netlify.app/?demo. Enquanto o projeto Supabase não estiver configurado, o endereço principal também abre a demonstração.
- **Especificação:** `docs/SPEC-RNQ-003-painel-admin.md`.

## Como funciona

```
Mac do Farley                              Supabase (São Paulo)                     Netlify
planilhas + formulários                    login (código por e-mail + MFA)
   │                                       banco com regras de acesso (RLS)         painel-novoquilombo
   └─ python3 atualizar.py ── decisões ◄── moderação (fonte da verdade) ◄────────── aprovar / recusar
                            ── visões  ──► painel por comunidade (PT e EN) ───────► ver a rede
                            ── site    ──────────────────────────────────────────► mapa-novoquilombo
```

- **O painel é a fonte da moderação.** As colunas `Publicar?`, `Incluir no mapa?`, `Aprovar?`, `Apresentação feita?` e `Encaminhado?` da planilha deixam de valer para os itens que já estão no painel.
- **Itens novos entram com a decisão da planilha.** Na primeira atualização, quem já tinha `Sim` entra como aprovado ("decidido na planilha").
- **Envios chegam sozinhos, na hora.** Cada inscrição, oferta, pedido, resposta ou participação enviada no mapa dispara um aviso do Netlify para a função `receber` do Supabase, que põe o item na Moderação com a marca "chegou pelo site". Não precisa abrir o terminal.
- **O mapa público se atualiza sozinho uma vez por dia.** Uma rotina no Mac (launchd) roda `atualizar.py` e `publicar.py` todo dia no horário escolhido (padrão 07:00). O painel mostra o horário da rotina e o resultado da última publicação. Se o Mac estiver desligado ou dormindo, a rotina roda quando ele acordar.
- **Os contatos ficam separados por comunidade.** Cada comunidade tem a sua própria visão. Um tecelão recebe só as visões e os itens das comunidades que tece, e o banco garante isso mesmo para quem tentar chamar a API direto.

## Papéis

| Papel | Vê | Faz |
|---|---|---|
| **Admin** | A rede toda, todas as comunidades, itens sem comunidade, equipe e histórico | Modera tudo, convida, define papéis e comunidades, tira e devolve acessos |
| **Tecelã(o)** | Só as comunidades atribuídas | Modera os itens dessas comunidades |

Regras que o banco garante:

- Só entra quem foi convidado.
- Admin sempre usa MFA.
- A rede nunca fica sem admin.
- Tirar o acesso de alguém vale na hora.
- O histórico não pode ser apagado, nem com a chave secreta.

## Preparar uma vez (cerca de 15 minutos)

Faça tudo no Mac, dentro da pasta `visao-publica`.

1. **Crie o projeto no Supabase.**
   1. Entre em https://supabase.com e faça a conta com o e-mail que você vai usar no painel.
   2. Clique em **New project**, escolha o nome `rnq-painel`, a região **South America (São Paulo)** e uma senha forte para o banco. Guarde a senha num gerenciador de senhas; o painel não precisa dela.
   3. Quando o projeto abrir, copie o **Project ref**: são as 20 letras do endereço, em `https://supabase.com/dashboard/project/<ref>`.

2. **Gere um token pessoal.** Vá em **Account → Access Tokens → Generate new token**. O token começa com `sbp_`.

3. **Preencha o `.env`.** Se ainda não existir, copie `env.exemplo` para `.env` e acrescente:
   ```
   SUPABASE_ACCESS_TOKEN=sbp_...
   SUPABASE_PROJECT_REF=<ref de 20 letras>
   RNQ_ADMIN_EMAIL=<seu e-mail>
   RNQ_ADMIN_NOME=Farley Lobo
   RNQ_PAINEL_URL=https://painel-novoquilombo.netlify.app
   ```
   O `.env` é privado e fica fora do GitHub.

4. **Prepare o banco e o login:**
   ```bash
   python3 painel_admin.py configurar
   ```
   O comando faz tudo isto:
   - cria o banco, as regras de acesso e o histórico;
   - configura o login: só por convite, código de 6 dígitos por e-mail e MFA;
   - grava a chave publicável em `admin/config.js` e a chave secreta só no `.env`;
   - publica a função de convite e a função `receber`;
   - cria a chave da função `receber` (`RNQ_RECEBER_SEGREDO`, só no `.env` e no Supabase);
   - liga os formulários do mapa no Netlify à função `receber` (precisa do `NETLIFY_TOKEN` e do `NETLIFY_SITE_ID`);
   - convida você como o primeiro admin.

   Pode rodar de novo a qualquer momento: nada é duplicado e nenhum convite é reenviado.

5. **Ponha o painel no ar:**
   ```bash
   python3 painel_admin.py publicar
   ```
   O comando usa o `NETLIFY_TOKEN` do `.env`. Sem o token, rode `python3 painel_admin.py publicar --so-pasta` e arraste a pasta `_trabalho/painel-admin` em **Netlify → painel-novoquilombo → Deploys**.

6. **Mande os dados:**
   ```bash
   python3 atualizar.py
   ```

7. **Ligue a atualização diária do mapa:**
   ```bash
   python3 painel_admin.py automatizar            # todo dia às 07:00
   python3 painel_admin.py automatizar --hora 21  # outro horário
   python3 painel_admin.py automatizar --desligar
   ```
   - O registro de cada execução fica em `~/Library/Logs/rnq-rotina.log`.
   - Para testar na hora: `launchctl kickstart gui/$(id -u)/org.novoquilombo.rotina`.
   - **Permissão do macOS (a confirmar no seu Mac):** se a pasta do projeto estiver na Mesa (Desktop) ou em Documentos, o macOS pode bloquear a rotina em segundo plano. Nesse caso o log mostra "Operation not permitted" e o painel mostra a falha. A solução é dar **Acesso Total ao Disco** ao `python3` em **Ajustes do Sistema → Privacidade e Segurança**, ou mover a pasta para fora da Mesa.

8. **Entre no painel.**
   1. Abra https://painel-novoquilombo.netlify.app, digite seu e-mail e clique no link do e-mail que chegar. Sem SMTP próprio, o e-mail é o padrão do Supabase, em inglês, com o link "Log In". Com SMTP, o e-mail sai em PT/EN e traz também um código de 6 dígitos.
   2. Na primeira vez, leia o QR code com um app autenticador (Google Authenticator, Microsoft Authenticator ou 1Password) e digite o código do app.

## O dia a dia

Com a automação ligada, o dia a dia é só o painel: os envios chegam na Moderação na hora, e o mapa público se atualiza sozinho uma vez por dia. Para publicar antes do horário:

```bash
python3 atualizar.py      # formulários -> decisões do painel -> site -> painel -> testes
python3 publicar.py       # o site público passa a mostrar o que foi aprovado
```

- **Ver o que chegou:** a Moderação recarrega sozinha quando você volta para a aba, e o botão **Atualizar lista** recarrega na hora.
- **Faixa do mapa:** no alto da Visão e da Moderação, o painel mostra o horário da rotina diária e a última publicação. Se a última publicação falhou, a faixa fica vermelha e diz em que etapa.

- **Moderar:** abra o painel na aba **Moderação**. Para cada item, use **Aprovar** ou **Recusar**, com um motivo opcional. Para as tarefas, use **Marcar como feito** ou **Não vai acontecer**. Os contatos ficam escondidos até você clicar em "Mostrar contatos".
- **Tecer:** a aba **Visão da rede** tem a saúde da rede, as apresentações sugeridas (com o botão "Copiar mensagem"), os pedidos em aberto e as pontes. Os botões no alto trocam entre a rede toda e cada comunidade.
- **Equipe:** a aba **Equipe** tem o formulário de convite (e-mail, papel e comunidades), e em cada pessoa dá para mudar o papel e as comunidades, ou tirar e devolver o acesso.
- **Histórico:** a aba **Histórico** mostra quem decidiu ou mudou o quê, e quando.
- **Sem internet ou com o Supabase fora do ar:** o `atualizar.py` não gera nada, para não publicar o que foi recusado. Em emergência, `python3 atualizar.py --sem-painel-admin` volta a usar só a planilha.
- **Conferir o painel:** `python3 painel_admin.py status`.

## Convidar outras pessoas: e-mail próprio (SMTP)

O e-mail padrão do Supabase só entrega para quem faz parte da equipe do projeto no Supabase, e no máximo 2 e-mails por hora. Para você, isso basta. Antes de convidar outras pessoas, configure um remetente próprio.

1. **Gmail da rede (rnqbrasil@gmail.com):**
   1. Ative a verificação em duas etapas na conta.
   2. Crie uma **senha de app** em https://myaccount.google.com/apppasswords.
   3. Acrescente ao `.env`:
      ```
      SMTP_HOST=smtp.gmail.com
      SMTP_PORT=587
      SMTP_USER=rnqbrasil@gmail.com
      SMTP_PASS=<senha de app>
      SMTP_SENDER_NAME=Rede Novo Quilombo
      ```
2. **Aplique a configuração:** rode `python3 painel_admin.py configurar` de novo.

Outros serviços (Resend, Brevo) funcionam do mesmo jeito: basta trocar o host, o usuário e a senha.

## Plano gratuito do Supabase

- **Pausa por falta de uso.** O plano gratuito pausa projetos parados por uma semana. Usar o painel e rodar o `atualizar.py` toda semana conta como uso. Para garantir, o fluxo `.github/workflows/painel-manter-ativo.yml` chama o banco a cada 3 dias. Para ligá-lo, crie no GitHub (**Settings → Secrets and variables → Actions**) os segredos `RNQ_SUPABASE_URL` e `RNQ_SUPABASE_CHAVE_PUBLICA`, com os valores de `admin/config.js`.
- **Limites (a verificar na página de preços do Supabase):** 500 MB de banco e 50 mil usuários por mês. Isso sobra para a rede.
- **Projeto pausado:** dá para reativá-lo no painel do Supabase.

## Segurança: o que protege o quê

| Risco | Proteção |
|---|---|
| Alguém de fora se cadastrar | Cadastro aberto desligado; o app pede o código com `shouldCreateUser: false`; quem não está na equipe não vê nenhuma linha (RLS) |
| Senha vazada | Não há senha: o login é por código de uso único por e-mail, e admin precisa do código do app autenticador (aal2), exigido pelo próprio banco |
| Tecelão ver outra comunidade | RLS em todas as tabelas e uma visão separada por comunidade, gerada no Mac só com as linhas daquela comunidade (testado contra vazamento) |
| Chave secreta no navegador | Ela fica só no `.env` do Mac e nos segredos da função. `publicar` e os testes recusam qualquer arquivo do app que contenha uma |
| Código malicioso na visão | A visão roda num iframe isolado (`sandbox`), sem acesso ao login, e a página tem uma CSP rígida (só scripts do próprio site, mais o script fixo da visão, liberado por hash) |
| Alterar o histórico | Gatilho no banco bloqueia alteração e exclusão para qualquer papel |
| Ficar sem admin | Gatilho no banco bloqueia rebaixar ou desativar o último admin |
| Quem saiu do mapa continuar no painel | Itens e contatos dessa pessoa são apagados na atualização seguinte (RF25) |

## LGPD

- **Base legal:** legítimo interesse. O contato de privacidade é rnqbrasil@gmail.com.
- **Atualize o aviso de privacidade.** Ele precisa dizer que os contatos ficam num banco em nuvem (Supabase, região São Paulo), acessado só pela equipe de tecelagem.
- **Tecelões fora do Brasil (por exemplo, June Holley):** o acesso pode configurar transferência internacional (art. 33). Valide a hipótese aplicável e atualize o aviso antes de convidar.
- **A verificar:** o acordo de tratamento de dados (DPA) do Supabase e onde ficam os backups.

## Para outras redes (código aberto)

O painel não tem nada específico da RNQ além dos textos.

1. Crie o seu projeto Supabase.
2. Rode `python3 painel_admin.py configurar` com o seu `.env`.
3. Publique a pasta `admin/` no seu Netlify.

O `admin/config.js` de cada instalação fica fora do repositório.

## Arquivos

```
admin/                       # o app (site estático, sem build)
  index.html app.js app.css i18n.js (PT/EN) api.js (Supabase) demo.js demo-dados.js (rede fictícia)
  config.js                  # gerado pelo configurar (fora do Git)
  vendor/supabase.js fonts/ img/  _headers netlify.toml (CSP e cabeçalhos de segurança)
  supabase/schema.sql        # banco: tabelas, RLS, funções rnq_*, travas
  supabase/functions/convidar/  index.ts (Deno) + logica.js (testada no Node)
  supabase/functions/receber/   index.ts + logica.js + contrato.json (envios do Netlify direto na Moderação)
rnq/admin.py                 # itens de moderação, recorte por comunidade, visões, sincronização
rnq/supabase.py              # conversa com o Supabase (só urllib)
painel_admin.py              # configurar · publicar · status · demo · ligar-formularios · automatizar · rotina
tests/sql/                   # banco (PGlite: Postgres de verdade em memória) e função de convite
tests/test_admin.py tests/test_painel_admin.py tests/test_receber.py (função receber = pipeline)
tests/e2e/painel.test.mjs    # navegador: demo, login, MFA, moderação, equipe, PT/EN, celular, CSP
```

## Testes

```bash
npm install
npm run test:py       # pipeline (inclui o painel admin)
npm run test:sql      # banco: regras de acesso, travas, sincronização; função de convite
npm run test:painel   # o painel num navegador de verdade, com a CSP do Netlify
npm test              # tudo, inclusive o site público
```

O teste `tests/sql/convidar-deno.test.mjs` roda a função de convite no Deno de verdade quando há Deno instalado (`DENO=/caminho/deno`). Sem Deno, ele é pulado.
