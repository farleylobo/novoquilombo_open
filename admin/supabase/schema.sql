-- =====================================================================================================
-- Painel admin da Rede Novo Quilombo — banco (Supabase / Postgres)
--
-- Idempotente: pode rodar de novo a cada versão (python3 painel_admin.py configurar faz isso).
-- Modelo de segurança (SPEC-RNQ-003):
--   * Ninguém escreve direto nas tabelas pelo navegador: toda escrita passa por funções rnq_* que
--     conferem a permissão e gravam a auditoria.
--   * Leitura por RLS: admin (com MFA, aal2) vê tudo; tecelão vê só as comunidades atribuídas.
--   * O pipeline do Mac usa a chave secreta (service_role) e só chama rnq_pipeline_*.
--   * A auditoria é só de acréscimo; a rede nunca fica sem admin ativo.
-- =====================================================================================================

-- ---------- tipos e tabelas ---------------------------------------------------------------------------
do $$ begin
  create type public.papel_equipe as enum ('admin', 'tecelao');
exception when duplicate_object then null; end $$;

create table if not exists public.rnq_meta (
  chave text primary key,
  valor text not null
);

create table if not exists public.equipe (
  user_id       uuid primary key references auth.users (id) on delete cascade,
  email         text not null unique,
  nome          text,
  papel         public.papel_equipe not null default 'tecelao',
  idioma        text not null default 'pt' check (idioma in ('pt', 'en')),
  ativo         boolean not null default true,
  criado_em     timestamptz not null default now(),
  convidado_por uuid,
  ultimo_acesso timestamptz
);

create table if not exists public.comunidades (
  id            text primary key,
  nome          text not null,
  nome_en       text,
  ativa         boolean not null default true,
  atualizado_em timestamptz not null default now()
);

create table if not exists public.equipe_comunidades (
  user_id       uuid not null references public.equipe (user_id) on delete cascade,
  comunidade_id text not null references public.comunidades (id) on delete cascade,
  primary key (user_id, comunidade_id)
);

-- escopo 'rede' = a rede toda (só admin); qualquer outro valor = id de uma comunidade
create table if not exists public.snapshots (
  escopo    text primary key,
  gerado_em timestamptz not null,
  resumo    jsonb not null default '{}'::jsonb,
  html_pt   text not null,
  html_en   text not null
);

create table if not exists public.moderacao (
  id                bigint generated always as identity primary key,
  tipo              text not null check (tipo in ('mural', 'perfil', 'ligacao', 'iniciativa', 'cadastro',
                                                  'resposta', 'participacao')),
  item_id           text not null,
  comunidades       text[] not null default '{}',
  titulo            text not null default '',
  conteudo          jsonb not null default '{}'::jsonb,   -- o que vai (ou iria) para o site
  privado           jsonb not null default '{}'::jsonb,   -- contatos e notas: só a equipe vê
  recebido_em       timestamptz,
  status            text not null default 'pendente' check (status in ('pendente', 'aprovado', 'recusado')),
  decidido_por      uuid,
  decidido_por_nome text,
  decidido_em       timestamptz,
  motivo            text,
  origem_decisao    text check (origem_decisao in ('painel', 'planilha')),
  criado_em         timestamptz not null default now(),
  atualizado_em     timestamptz not null default now(),
  unique (tipo, item_id)
);
-- fonte: 'site' = chegou na hora pelo formulário (Edge Function "receber"); 'planilha' = já passou pelo Mac.
alter table public.moderacao add column if not exists fonte text not null default 'planilha';
create index if not exists moderacao_status_idx on public.moderacao (status);
create index if not exists moderacao_comunidades_idx on public.moderacao using gin (comunidades);

create table if not exists public.auditoria (
  id         bigint generated always as identity primary key,
  quando     timestamptz not null default now(),
  quem       uuid,
  quem_email text,
  acao       text not null,
  alvo       text,
  detalhes   jsonb not null default '{}'::jsonb
);
create index if not exists auditoria_quando_idx on public.auditoria (quando desc);

insert into public.rnq_meta (chave, valor) values ('schema_versao', '2')
  on conflict (chave) do update set valor = excluded.valor;

-- ---------- funções de apoio (usadas pelas políticas) -------------------------------------------------
create or replace function public.rnq_eu_ativo() returns boolean
language sql stable security definer set search_path = public, pg_temp as $$
  select exists (select 1 from public.equipe e where e.user_id = auth.uid() and e.ativo);
$$;

-- Sessão com MFA (aal2) quando é exigido: admin sempre; tecelão se tiver cadastrado um fator.
create or replace function public.rnq_sessao_ok() returns boolean
language sql stable security definer set search_path = public, pg_temp as $$
  select coalesce(auth.jwt() ->> 'aal', '') = 'aal2'
      or (
        not exists (select 1 from public.equipe e where e.user_id = auth.uid() and e.papel = 'admin')
        and not exists (select 1 from auth.mfa_factors f where f.user_id = auth.uid() and f.status = 'verified')
      );
$$;

create or replace function public.rnq_eh_admin() returns boolean
language sql stable security definer set search_path = public, pg_temp as $$
  select exists (select 1 from public.equipe e where e.user_id = auth.uid() and e.ativo and e.papel = 'admin')
     and coalesce(auth.jwt() ->> 'aal', '') = 'aal2';
$$;

create or replace function public.rnq_minhas_comunidades() returns text[]
language sql stable security definer set search_path = public, pg_temp as $$
  select coalesce(array_agg(ec.comunidade_id order by ec.comunidade_id), '{}')
    from public.equipe_comunidades ec
    join public.equipe e on e.user_id = ec.user_id
   where e.user_id = auth.uid() and e.ativo;
$$;

create or replace function public.rnq_pode_ver(p_comunidades text[]) returns boolean
language sql stable security definer set search_path = public, pg_temp as $$
  select public.rnq_eh_admin()
      or (public.rnq_eu_ativo() and public.rnq_sessao_ok()
          and coalesce(p_comunidades, '{}') && public.rnq_minhas_comunidades());
$$;

create or replace function public.rnq_auditar(p_acao text, p_alvo text, p_detalhes jsonb) returns void
language sql security definer set search_path = public, pg_temp as $$
  insert into public.auditoria (quem, quem_email, acao, alvo, detalhes)
  values (auth.uid(), (select email from public.equipe where user_id = auth.uid()), p_acao, p_alvo,
          coalesce(p_detalhes, '{}'::jsonb));
$$;

-- ---------- travas ----------------------------------------------------------------------------------
-- Auditoria só de acréscimo: ninguém altera nem apaga (nem a chave secreta).
create or replace function public.rnq_auditoria_imutavel() returns trigger
language plpgsql as $$
begin
  raise exception 'A auditoria não pode ser alterada nem apagada' using errcode = '42501';
end $$;
drop trigger if exists auditoria_imutavel on public.auditoria;
create trigger auditoria_imutavel before update or delete on public.auditoria
  for each row execute function public.rnq_auditoria_imutavel();

-- A rede nunca fica sem admin ativo (RF28).
create or replace function public.rnq_guardar_ultimo_admin() returns trigger
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  era_admin boolean := old.papel = 'admin' and old.ativo;
  continua  boolean := tg_op = 'UPDATE' and new.papel = 'admin' and new.ativo;
begin
  if era_admin and not continua and not exists (
       select 1 from public.equipe e where e.user_id <> old.user_id and e.papel = 'admin' and e.ativo) then
    raise exception 'A rede precisa de pelo menos um admin ativo' using errcode = 'P0001';
  end if;
  return case when tg_op = 'DELETE' then old else new end;
end $$;
drop trigger if exists equipe_ultimo_admin on public.equipe;
create trigger equipe_ultimo_admin before update or delete on public.equipe
  for each row execute function public.rnq_guardar_ultimo_admin();

-- ---------- RLS ---------------------------------------------------------------------------------------
alter table public.rnq_meta enable row level security;
alter table public.equipe enable row level security;
alter table public.comunidades enable row level security;
alter table public.equipe_comunidades enable row level security;
alter table public.snapshots enable row level security;
alter table public.moderacao enable row level security;
alter table public.auditoria enable row level security;

drop policy if exists equipe_ler on public.equipe;
create policy equipe_ler on public.equipe for select to authenticated
  using ((user_id = auth.uid() and ativo) or public.rnq_eh_admin());

drop policy if exists comunidades_ler on public.comunidades;
create policy comunidades_ler on public.comunidades for select to authenticated
  using (public.rnq_eu_ativo() and public.rnq_sessao_ok());

drop policy if exists equipe_comunidades_ler on public.equipe_comunidades;
create policy equipe_comunidades_ler on public.equipe_comunidades for select to authenticated
  using ((user_id = auth.uid() and public.rnq_eu_ativo()) or public.rnq_eh_admin());

drop policy if exists snapshots_ler on public.snapshots;
create policy snapshots_ler on public.snapshots for select to authenticated
  using (public.rnq_eh_admin() or (escopo <> 'rede' and public.rnq_pode_ver(array[escopo])));

drop policy if exists moderacao_ler on public.moderacao;
create policy moderacao_ler on public.moderacao for select to authenticated
  using (public.rnq_pode_ver(comunidades));

drop policy if exists auditoria_ler on public.auditoria;
create policy auditoria_ler on public.auditoria for select to authenticated
  using (public.rnq_eh_admin());
-- (sem políticas de insert/update/delete: o navegador nunca escreve direto nas tabelas)

-- ---------- funções do painel (navegador, usuário logado) ---------------------------------------------
create or replace function public.rnq_meu_perfil() returns jsonb
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  eu public.equipe;
begin
  select * into eu from public.equipe where user_id = auth.uid();
  if eu.user_id is null or not eu.ativo then
    return null;
  end if;
  update public.equipe set ultimo_acesso = now() where user_id = eu.user_id;
  return jsonb_build_object(
    'user_id', eu.user_id, 'email', eu.email, 'nome', eu.nome, 'papel', eu.papel, 'idioma', eu.idioma,
    'comunidades', to_jsonb(public.rnq_minhas_comunidades()),
    'mfa_exigido', eu.papel = 'admin'
                   or exists (select 1 from auth.mfa_factors f where f.user_id = eu.user_id and f.status = 'verified'),
    'sessao_ok', public.rnq_sessao_ok());
end $$;

create or replace function public.rnq_definir_idioma(p_idioma text) returns void
language plpgsql security definer set search_path = public, pg_temp as $$
begin
  if p_idioma not in ('pt', 'en') then
    raise exception 'Idioma inválido' using errcode = '22023';
  end if;
  update public.equipe set idioma = p_idioma where user_id = auth.uid() and ativo;
end $$;

create or replace function public.rnq_decidir(p_id bigint, p_status text, p_motivo text default null)
returns public.moderacao
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  item public.moderacao;
  antes text;
  nome_eu text;
begin
  if p_status not in ('aprovado', 'recusado', 'pendente') then
    raise exception 'Status inválido' using errcode = '22023';
  end if;
  select * into item from public.moderacao where id = p_id for update;
  if item.id is null or not public.rnq_pode_ver(item.comunidades) then
    raise exception 'Sem permissão para decidir este item' using errcode = '42501';
  end if;
  if p_status = 'aprovado' and nullif(item.conteudo ->> 'bloqueio', '') is not null then   -- RF26
    raise exception 'Este item não pode ser aprovado (%)', item.conteudo ->> 'bloqueio' using errcode = '22023';
  end if;
  antes := item.status;
  select coalesce(nullif(nome, ''), email) into nome_eu from public.equipe where user_id = auth.uid();
  update public.moderacao set
      status = p_status,
      motivo = case when p_status = 'pendente' then null else nullif(trim(coalesce(p_motivo, '')), '') end,
      decidido_por = case when p_status = 'pendente' then null else auth.uid() end,
      decidido_por_nome = case when p_status = 'pendente' then null else nome_eu end,
      decidido_em = case when p_status = 'pendente' then null else now() end,
      origem_decisao = case when p_status = 'pendente' then null else 'painel' end,
      atualizado_em = now()
    where id = p_id
    returning * into item;
  perform public.rnq_auditar('moderacao.decidir', item.tipo || ':' || item.item_id,
    jsonb_build_object('de', antes, 'para', p_status, 'motivo', item.motivo, 'titulo', item.titulo));
  return item;
end $$;

create or replace function public.rnq_equipe_listar() returns jsonb
language plpgsql security definer set search_path = public, pg_temp as $$
begin
  if not public.rnq_eh_admin() then
    raise exception 'Só admin vê a equipe' using errcode = '42501';
  end if;
  return coalesce((
    select jsonb_agg(jsonb_build_object(
             'user_id', e.user_id, 'email', e.email, 'nome', e.nome, 'papel', e.papel, 'idioma', e.idioma,
             'ativo', e.ativo, 'criado_em', e.criado_em, 'ultimo_acesso', e.ultimo_acesso,
             'comunidades', coalesce((select jsonb_agg(ec.comunidade_id order by ec.comunidade_id)
                                        from public.equipe_comunidades ec where ec.user_id = e.user_id), '[]'::jsonb),
             'mfa', exists (select 1 from auth.mfa_factors f where f.user_id = e.user_id and f.status = 'verified'))
           order by e.ativo desc, e.papel, lower(coalesce(e.nome, e.email)))
      from public.equipe e), '[]'::jsonb);
end $$;

create or replace function public.rnq_equipe_atualizar(
  p_user uuid, p_papel text default null, p_ativo boolean default null,
  p_comunidades text[] default null, p_nome text default null)
returns jsonb
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  antes public.equipe;
  depois public.equipe;
  coms_antes text[];
  coms_depois text[];
begin
  if not public.rnq_eh_admin() then
    raise exception 'Só admin muda a equipe' using errcode = '42501';
  end if;
  select * into antes from public.equipe where user_id = p_user for update;
  if antes.user_id is null then
    raise exception 'Pessoa não encontrada na equipe' using errcode = 'P0002';
  end if;
  if p_papel is not null and p_papel not in ('admin', 'tecelao') then
    raise exception 'Papel inválido' using errcode = '22023';
  end if;
  if p_comunidades is not null and exists (
       select 1 from unnest(p_comunidades) c where c not in (select id from public.comunidades)) then
    raise exception 'Comunidade desconhecida' using errcode = '22023';
  end if;
  select coalesce(array_agg(comunidade_id order by comunidade_id), '{}') into coms_antes
    from public.equipe_comunidades where user_id = p_user;

  update public.equipe set
      papel = coalesce(p_papel::public.papel_equipe, papel),
      ativo = coalesce(p_ativo, ativo),
      nome = coalesce(nullif(trim(coalesce(p_nome, '')), ''), nome)
    where user_id = p_user
    returning * into depois;

  if p_comunidades is not null then
    delete from public.equipe_comunidades where user_id = p_user;
    insert into public.equipe_comunidades (user_id, comunidade_id)
      select p_user, c from (select distinct unnest(p_comunidades) c) x;
  end if;
  select coalesce(array_agg(comunidade_id order by comunidade_id), '{}') into coms_depois
    from public.equipe_comunidades where user_id = p_user;

  -- RF29: desativar encerra as sessões. O acesso aos dados já cai na hora pela RLS (ativo = false);
  -- apagar as sessões impede renovar o login. Melhor esforço: se o banco não permitir, a RLS segue valendo.
  if antes.ativo and not depois.ativo then
    begin
      delete from auth.sessions where user_id = p_user;
    exception when others then null;
    end;
  end if;

  perform public.rnq_auditar('equipe.atualizar', depois.email, jsonb_build_object(
    'papel', jsonb_build_array(antes.papel, depois.papel),
    'ativo', jsonb_build_array(antes.ativo, depois.ativo),
    'comunidades', jsonb_build_array(coms_antes, coms_depois),
    'nome', jsonb_build_array(antes.nome, depois.nome)));
  return jsonb_build_object('user_id', depois.user_id, 'papel', depois.papel, 'ativo', depois.ativo,
                            'comunidades', to_jsonb(coms_depois));
end $$;

-- ---------- funções do servidor (só a chave secreta / Edge Function / pipeline do Mac) ----------------
create or replace function public.rnq_usuario_por_email(p_email text) returns uuid
language sql stable security definer set search_path = public, pg_temp as $$
  select id from auth.users where lower(email) = lower(trim(p_email)) limit 1;
$$;

-- Registra (ou reativa) alguém convidado. Chamado pela Edge Function "convidar" depois do convite,
-- e pelo "painel_admin.py configurar" para o primeiro admin.
create or replace function public.rnq_convite_registrar(
  p_user uuid, p_email text, p_nome text, p_papel text, p_comunidades text[],
  p_idioma text default 'pt', p_convidado_por uuid default null)
returns jsonb
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  existia boolean;
begin
  if p_papel not in ('admin', 'tecelao') then
    raise exception 'Papel inválido' using errcode = '22023';
  end if;
  if exists (select 1 from unnest(coalesce(p_comunidades, '{}')) c where c not in (select id from public.comunidades)) then
    raise exception 'Comunidade desconhecida' using errcode = '22023';
  end if;
  select exists (select 1 from public.equipe where user_id = p_user) into existia;
  insert into public.equipe (user_id, email, nome, papel, idioma, ativo, convidado_por)
    values (p_user, lower(trim(p_email)), nullif(trim(coalesce(p_nome, '')), ''), p_papel::public.papel_equipe,
            case when p_idioma in ('pt', 'en') then p_idioma else 'pt' end, true, p_convidado_por)
    on conflict (user_id) do update set
      email = excluded.email, nome = coalesce(excluded.nome, public.equipe.nome),
      papel = excluded.papel, ativo = true;
  delete from public.equipe_comunidades where user_id = p_user;
  insert into public.equipe_comunidades (user_id, comunidade_id)
    select p_user, c from (select distinct unnest(coalesce(p_comunidades, '{}')) c) x;
  insert into public.auditoria (quem, quem_email, acao, alvo, detalhes)
    values (p_convidado_por, (select email from public.equipe where user_id = p_convidado_por),
            case when existia then 'equipe.reconvidar' else 'equipe.convidar' end, lower(trim(p_email)),
            jsonb_build_object('papel', p_papel, 'comunidades', to_jsonb(coalesce(p_comunidades, '{}'))));
  return jsonb_build_object('user_id', p_user, 'novo', not existia);
end $$;

-- Decisões já tomadas, para o pipeline aplicar antes de gerar o site (D5: o painel é a fonte da moderação).
create or replace function public.rnq_pipeline_decisoes() returns jsonb
language sql stable security definer set search_path = public, pg_temp as $$
  select coalesce(jsonb_agg(jsonb_build_object(
           'tipo', tipo, 'item_id', item_id, 'status', status, 'motivo', motivo,
           'decidido_por_nome', decidido_por_nome, 'decidido_em', decidido_em, 'origem', origem_decisao)
           order by tipo, item_id), '[]'::jsonb)
    from public.moderacao;
$$;

-- Sincronização completa vinda do Mac. p = {gerado_em, comunidades: [...], itens: [...], snapshots: [...]}
--   itens novos entram com a decisão que a planilha já tinha (migração única: "origem_decisao = planilha");
--   itens que já existem só têm o conteúdo atualizado (a decisão do painel nunca é sobrescrita);
--   itens que sumiram da planilha (ou de quem saiu do mapa, RF25) são apagados;
--   snapshots são substituídos por inteiro.
create or replace function public.rnq_pipeline_sincronizar(p jsonb) returns jsonb
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  n_novos int; n_atualizados int; n_apagados int; n_snap int; n_coms int;
begin
  if p is null or jsonb_typeof(p -> 'itens') <> 'array' or jsonb_typeof(p -> 'snapshots') <> 'array' then
    raise exception 'Formato de sincronização inválido' using errcode = '22023';
  end if;

  -- comunidades
  insert into public.comunidades (id, nome, nome_en, ativa, atualizado_em)
    select c ->> 'id', c ->> 'nome', nullif(c ->> 'nome_en', ''), true, now()
      from jsonb_array_elements(coalesce(p -> 'comunidades', '[]'::jsonb)) c
    on conflict (id) do update set nome = excluded.nome, nome_en = excluded.nome_en, ativa = true,
                                   atualizado_em = now();
  get diagnostics n_coms = row_count;
  update public.comunidades set ativa = false
    where id not in (select c ->> 'id' from jsonb_array_elements(coalesce(p -> 'comunidades', '[]'::jsonb)) c);

  -- itens
  drop table if exists pg_temp._itens;
  create temporary table _itens on commit drop as
    select i ->> 'tipo' as tipo, i ->> 'item_id' as item_id,
           coalesce((select array_agg(x) from jsonb_array_elements_text(coalesce(i -> 'comunidades', '[]'::jsonb)) x), '{}') as comunidades,
           coalesce(i ->> 'titulo', '') as titulo, coalesce(i -> 'conteudo', '{}'::jsonb) as conteudo,
           coalesce(i -> 'privado', '{}'::jsonb) as privado, nullif(i ->> 'recebido_em', '')::timestamptz as recebido_em,
           coalesce(i ->> 'status_planilha', 'pendente') as status_planilha
      from jsonb_array_elements(p -> 'itens') i;

  update public.moderacao m set comunidades = t.comunidades, titulo = t.titulo, conteudo = t.conteudo,
         privado = t.privado, recebido_em = t.recebido_em, fonte = 'planilha', atualizado_em = now()
    from _itens t
   where m.tipo = t.tipo and m.item_id = t.item_id
     and (m.comunidades, m.titulo, m.conteudo, m.privado, m.recebido_em, m.fonte)
         is distinct from (t.comunidades, t.titulo, t.conteudo, t.privado, t.recebido_em, 'planilha');
  get diagnostics n_atualizados = row_count;

  insert into public.moderacao (tipo, item_id, comunidades, titulo, conteudo, privado, recebido_em, status,
                                decidido_em, decidido_por_nome, origem_decisao)
    select t.tipo, t.item_id, t.comunidades, t.titulo, t.conteudo, t.privado, t.recebido_em,
           case when t.status_planilha in ('aprovado', 'recusado') then t.status_planilha else 'pendente' end,
           case when t.status_planilha in ('aprovado', 'recusado') then now() end,
           case when t.status_planilha in ('aprovado', 'recusado') then 'planilha' end,
           case when t.status_planilha in ('aprovado', 'recusado') then 'planilha' end
      from _itens t
     where not exists (select 1 from public.moderacao m where m.tipo = t.tipo and m.item_id = t.item_id);
  get diagnostics n_novos = row_count;

  -- só apaga o que já tinha passado pela planilha: o que acabou de chegar pelo site ainda não está lá
  delete from public.moderacao m
   where m.fonte = 'planilha'
     and not exists (select 1 from _itens t where t.tipo = m.tipo and t.item_id = m.item_id);
  get diagnostics n_apagados = row_count;

  -- snapshots
  delete from public.snapshots
   where escopo not in (select s ->> 'escopo' from jsonb_array_elements(p -> 'snapshots') s);
  insert into public.snapshots (escopo, gerado_em, resumo, html_pt, html_en)
    select s ->> 'escopo', coalesce(nullif(p ->> 'gerado_em', '')::timestamptz, now()),
           coalesce(s -> 'resumo', '{}'::jsonb), s ->> 'html_pt', s ->> 'html_en'
      from jsonb_array_elements(p -> 'snapshots') s
    on conflict (escopo) do update set gerado_em = excluded.gerado_em, resumo = excluded.resumo,
                                       html_pt = excluded.html_pt, html_en = excluded.html_en;
  get diagnostics n_snap = row_count;

  insert into public.auditoria (acao, alvo, detalhes)
    values ('pipeline.sincronizar', 'rede', jsonb_build_object(
      'itens_novos', n_novos, 'itens_atualizados', n_atualizados, 'itens_apagados', n_apagados,
      'snapshots', n_snap, 'comunidades', n_coms));
  return jsonb_build_object('itens_novos', n_novos, 'itens_atualizados', n_atualizados,
                            'itens_apagados', n_apagados, 'snapshots', n_snap, 'comunidades', n_coms);
end $$;

-- Envios que chegam na hora pelo site (Edge Function "receber", com a chave secreta).
-- p = {itens: [...]} no mesmo formato da sincronização. Nunca sobrescreve o que já existe (a planilha e as
-- decisões do painel valem mais). "Posso ajudar" e participações herdam as comunidades do item a que respondem.
create or replace function public.rnq_receber_envio(p jsonb) returns jsonb
language plpgsql security definer set search_path = public, pg_temp as $$
declare
  i jsonb;
  coms text[];
  novos int := 0;
  ref_tipo text;
begin
  if p is null or jsonb_typeof(p -> 'itens') <> 'array' then
    raise exception 'Formato de envio inválido' using errcode = '22023';
  end if;
  for i in select * from jsonb_array_elements(p -> 'itens') loop
    coms := coalesce((select array_agg(x) from jsonb_array_elements_text(coalesce(i -> 'comunidades', '[]'::jsonb)) x), '{}');
    if coms = '{}' and nullif(i ->> 'ref', '') is not null then
      ref_tipo := case i ->> 'tipo' when 'resposta' then 'mural' when 'participacao' then 'iniciativa' end;
      select m.comunidades into coms from public.moderacao m where m.tipo = ref_tipo and m.item_id = i ->> 'ref';
      coms := coalesce(coms, '{}');
    end if;
    insert into public.moderacao (tipo, item_id, comunidades, titulo, conteudo, privado, recebido_em, fonte)
      values (i ->> 'tipo', i ->> 'item_id', coms, coalesce(i ->> 'titulo', ''), coalesce(i -> 'conteudo', '{}'::jsonb),
              coalesce(i -> 'privado', '{}'::jsonb), nullif(i ->> 'recebido_em', '')::timestamptz, 'site')
      on conflict (tipo, item_id) do nothing;
    if found then
      novos := novos + 1;
      insert into public.auditoria (acao, alvo, detalhes)
        values ('site.envio', (i ->> 'tipo') || ':' || (i ->> 'item_id'), jsonb_build_object('titulo', i ->> 'titulo'));
    end if;
  end loop;
  return jsonb_build_object('novos', novos);
end $$;

-- O que o Mac fez por último (atualização, publicação do mapa, rotina diária), para o painel mostrar.
create or replace function public.rnq_pipeline_registrar(p_chave text, p_valor jsonb) returns void
language plpgsql security definer set search_path = public, pg_temp as $$
begin
  if p_chave not in ('ultima_publicacao', 'rotina_diaria') then
    raise exception 'Chave inválida' using errcode = '22023';
  end if;
  insert into public.rnq_meta (chave, valor) values (p_chave, p_valor::text)
    on conflict (chave) do update set valor = excluded.valor;
end $$;

create or replace function public.rnq_painel_status() returns jsonb
language sql stable security definer set search_path = public, pg_temp as $$
  select case when public.rnq_eu_ativo() and public.rnq_sessao_ok() then jsonb_build_object(
    'ultima_atualizacao', (select max(gerado_em) from public.snapshots),
    'ultima_publicacao', (select valor::jsonb from public.rnq_meta where chave = 'ultima_publicacao'),
    'rotina_diaria', (select valor::jsonb from public.rnq_meta where chave = 'rotina_diaria'))
  end;
$$;

-- Para o "manter ativo" (o plano gratuito pausa projetos parados) e para conferir a conexão.
create or replace function public.rnq_ping() returns jsonb
language sql stable security definer set search_path = public, pg_temp as $$
  select jsonb_build_object('ok', true, 'schema', (select valor from public.rnq_meta where chave = 'schema_versao'));
$$;

-- Resumo para "painel_admin.py status" (só a chave secreta).
create or replace function public.rnq_pipeline_status() returns jsonb
language sql stable security definer set search_path = public, pg_temp as $$
  select jsonb_build_object(
    'schema', (select valor from public.rnq_meta where chave = 'schema_versao'),
    'equipe', (select count(*) from public.equipe where ativo),
    'admins', (select count(*) from public.equipe where ativo and papel = 'admin'),
    'pendentes', (select count(*) from public.moderacao where status = 'pendente'),
    'itens', (select count(*) from public.moderacao),
    'ultimo_snapshot', (select max(gerado_em) from public.snapshots),
    'comunidades', (select count(*) from public.comunidades where ativa));
$$;

-- ---------- permissões --------------------------------------------------------------------------------
revoke all on public.rnq_meta, public.equipe, public.comunidades, public.equipe_comunidades, public.snapshots,
              public.moderacao, public.auditoria from anon, authenticated;
grant select on public.equipe, public.comunidades, public.equipe_comunidades, public.snapshots,
                public.moderacao, public.auditoria to authenticated;
grant all on public.rnq_meta, public.equipe, public.comunidades, public.equipe_comunidades, public.snapshots,
             public.moderacao, public.auditoria to service_role;

do $$
declare f record;
begin
  for f in select p.oid::regprocedure as sig from pg_proc p join pg_namespace n on n.oid = p.pronamespace
            where n.nspname = 'public' and p.proname like 'rnq\_%' loop
    execute format('revoke all on function %s from public, anon, authenticated', f.sig);
    execute format('grant execute on function %s to service_role', f.sig);
  end loop;
end $$;

-- usadas dentro das políticas (rodam com o papel de quem consulta) e pelo app
grant execute on function public.rnq_eu_ativo(), public.rnq_sessao_ok(), public.rnq_eh_admin(),
  public.rnq_minhas_comunidades(), public.rnq_pode_ver(text[]),
  public.rnq_meu_perfil(), public.rnq_definir_idioma(text), public.rnq_decidir(bigint, text, text),
  public.rnq_equipe_listar(), public.rnq_equipe_atualizar(uuid, text, boolean, text[], text),
  public.rnq_painel_status()
  to authenticated;
grant execute on function public.rnq_ping() to anon, authenticated;
