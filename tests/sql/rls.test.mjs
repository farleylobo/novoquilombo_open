// Testes do banco do painel admin (admin/supabase/schema.sql) num Postgres de verdade, rodando em memória (PGlite).
// Conferem as regras de acesso (RLS), as travas e a sincronização do pipeline — o coração da segurança do painel.
// Uso: node --test tests/sql/   (ou npm run test:sql)
import { test, before } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { PGlite } from '@electric-sql/pglite';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const ler = p => fs.readFileSync(path.join(RAIZ, p), 'utf8');

const U = {
  farley: '00000000-0000-0000-0000-00000000000a',
  june: '00000000-0000-0000-0000-00000000000b',
  tecA: '00000000-0000-0000-0000-0000000000c1',
  tecB: '00000000-0000-0000-0000-0000000000c2',
  fora: '00000000-0000-0000-0000-0000000000f0',
};

let db;

async function papel(role, claims = null) {
  await db.exec('reset role');
  await db.query("select set_config('request.jwt.claims', $1, false)", [claims ? JSON.stringify(claims) : '']);
  await db.exec(`set role ${role}`);
}
const como = (uid, aal = 'aal1') => papel('authenticated', { sub: uid, role: 'authenticated', aal });
const servico = () => papel('service_role', { role: 'service_role' });
const anonimo = () => papel('anon', { role: 'anon' });
const dono = async () => { await db.exec('reset role'); };   // como o Supabase faz com auth.*: fora do alcance do app
const sql = async (q, p = []) => (await db.query(q, p)).rows;
const um = async (q, p = []) => (await sql(q, p))[0];
async function falha(promessa, trecho) {
  await assert.rejects(promessa, e => {
    if (trecho && !String(e.message).toLowerCase().includes(trecho.toLowerCase())) {
      throw new Error(`erro inesperado: ${e.message}`);
    }
    return true;
  });
}

const ITENS = [
  { tipo: 'mural', item_id: 'm-tec', comunidades: ['tecnologia'], titulo: 'Mentoria em dados',
    conteudo: { tipo: 'Oferta' }, privado: { contato: 'ana@tec.org' }, status_planilha: 'pendente' },
  { tipo: 'cadastro', item_id: 'c-esg', comunidades: ['esg'], titulo: 'Bruno Esg',
    conteudo: {}, privado: { contato: 'bruno@esg.org' }, status_planilha: 'pendente' },
  { tipo: 'perfil', item_id: 'p-sem', comunidades: [], titulo: 'Sem comunidade',
    conteudo: {}, privado: { contato: 'sem@x.org' }, status_planilha: 'pendente' },
  { tipo: 'cadastro', item_id: 'c-fora', comunidades: ['esg'], titulo: 'Fora do mapa',
    conteudo: { bloqueio: 'fora_do_mapa' }, privado: {}, status_planilha: 'pendente' },
  { tipo: 'iniciativa', item_id: 'i-ja', comunidades: ['tecnologia', 'esg'], titulo: 'Já aprovada',
    conteudo: {}, privado: {}, status_planilha: 'aprovado' },
];
const SNAPS = [
  { escopo: 'rede', resumo: { pessoas: 10 }, html_pt: '<p>rede</p>', html_en: '<p>network</p>' },
  { escopo: 'tecnologia', resumo: { pessoas: 4 }, html_pt: '<p>tec</p>', html_en: '<p>tech</p>' },
  { escopo: 'esg', resumo: { pessoas: 3 }, html_pt: '<p>esg</p>', html_en: '<p>esg</p>' },
];
const COMS = [{ id: 'tecnologia', nome: 'Tecnologia', nome_en: 'Technology' },
              { id: 'esg', nome: 'ESG', nome_en: 'ESG' }, { id: 'teoria-u', nome: 'Teoria U', nome_en: 'Theory U' }];
const sincronizar = (itens = ITENS, snaps = SNAPS, coms = COMS) =>
  um('select rnq_pipeline_sincronizar($1::jsonb) as r',
     [JSON.stringify({ gerado_em: '2026-10-15T10:00:00Z', comunidades: coms, itens, snapshots: snaps })]);

before(async () => {
  db = new PGlite();
  await db.exec(ler('tests/sql/supabase-shim.sql'));
  await db.exec(ler('admin/supabase/schema.sql'));
  await db.exec(ler('admin/supabase/schema.sql'));            // roda duas vezes: tem de ser idempotente
  for (const [nome, id] of Object.entries(U)) {
    await db.query('insert into auth.users (id, email) values ($1, $2)', [id, `${nome}@exemplo.org`]);
  }
  await db.query("insert into auth.mfa_factors (user_id, status) values ($1, 'verified')", [U.farley]);
  await servico();
  await sincronizar();
  await sql("select rnq_convite_registrar($1, 'farley@exemplo.org', 'Farley', 'admin', '{}', 'pt', null)", [U.farley]);
  await sql("select rnq_convite_registrar($1, 'teca@exemplo.org', 'Tecelã A', 'tecelao', '{tecnologia}', 'pt', $2)", [U.tecA, U.farley]);
  await sql("select rnq_convite_registrar($1, 'tecb@exemplo.org', 'Tecelão B', 'tecelao', '{esg}', 'en', $2)", [U.tecB, U.farley]);
});

test('schema roda duas vezes sem erro e responde ao ping (anônimo)', async () => {
  await anonimo();
  const r = await um('select rnq_ping() as p');
  assert.deepEqual(r.p, { ok: true, schema: '2' });
});

test('anônimo não lê nenhuma tabela', async () => {
  await anonimo();
  for (const t of ['equipe', 'comunidades', 'snapshots', 'moderacao', 'auditoria', 'equipe_comunidades']) {
    await falha(sql(`select * from ${t}`), 'permission denied');
  }
});

test('CA23: quem tem login mas não foi convidado não vê nada nem decide', async () => {
  await como(U.fora, 'aal2');
  assert.equal((await um('select rnq_meu_perfil() as p')).p, null);
  assert.equal((await sql('select * from snapshots')).length, 0);
  assert.equal((await sql('select * from moderacao')).length, 0);
  assert.equal((await sql('select * from comunidades')).length, 0);
  const id = (await sql("select id from moderacao")).length;
  assert.equal(id, 0);
  await falha(sql("select rnq_decidir(1, 'aprovado', null)"), 'sem permissão');
});

test('CA20: tecelão vê só as suas comunidades (snapshots e moderação)', async () => {
  await como(U.tecA);
  const snaps = (await sql('select escopo from snapshots order by escopo')).map(r => r.escopo);
  assert.deepEqual(snaps, ['tecnologia']);
  const itens = (await sql('select item_id from moderacao order by item_id')).map(r => r.item_id);
  assert.deepEqual(itens, ['i-ja', 'm-tec']);                     // i-ja está em tecnologia e esg
  const perfil = (await um('select rnq_meu_perfil() as p')).p;
  assert.equal(perfil.papel, 'tecelao');
  assert.deepEqual(perfil.comunidades, ['tecnologia']);
  assert.equal(perfil.sessao_ok, true);
  assert.equal(perfil.mfa_exigido, false);
});

test('CA20: tecelão não decide item de outra comunidade, nem por chamada direta', async () => {
  await servico();
  const esg = (await um("select id from moderacao where item_id = 'c-esg'")).id;
  await como(U.tecA);
  await falha(sql("select rnq_decidir($1, 'aprovado', null)", [esg]), 'sem permissão');
  await falha(sql("update moderacao set status = 'aprovado' where id = $1", [esg]), 'permission denied');
});

test('D9: tecelão aprova item da própria comunidade e fica na auditoria', async () => {
  await servico();
  const tec = (await um("select id from moderacao where item_id = 'm-tec'")).id;
  await como(U.tecA);
  const r = await um("select (rnq_decidir($1, 'aprovado', 'ok')).*", [tec]);
  assert.equal(r.status, 'aprovado');
  assert.equal(r.origem_decisao, 'painel');
  assert.equal(r.decidido_por_nome, 'Tecelã A');
  await servico();
  const a = await um("select * from auditoria where acao = 'moderacao.decidir' order by id desc limit 1");
  assert.equal(a.alvo, 'mural:m-tec');
  assert.equal(a.quem, U.tecA);
  assert.equal(a.detalhes.para, 'aprovado');
});

test('desfazer (voltar para pendente) limpa quem decidiu', async () => {
  await servico();
  const tec = (await um("select id from moderacao where item_id = 'm-tec'")).id;
  await como(U.tecA);
  const r = await um("select (rnq_decidir($1, 'pendente', 'x')).*", [tec]);
  assert.equal(r.status, 'pendente');
  assert.equal(r.decidido_por, null);
  assert.equal(r.motivo, null);
  await falha(sql("select rnq_decidir($1, 'publicado', null)", [tec]), 'inválido');
});

test('admin sem MFA (aal1) não vê dados nem a equipe', async () => {
  await como(U.farley, 'aal1');
  const p = (await um('select rnq_meu_perfil() as p')).p;
  assert.equal(p.papel, 'admin');
  assert.equal(p.mfa_exigido, true);
  assert.equal(p.sessao_ok, false);
  assert.equal((await sql('select * from snapshots')).length, 0);
  assert.equal((await sql('select * from moderacao')).length, 0);
  await falha(sql('select rnq_equipe_listar()'), 'só admin');
});

test('admin com MFA (aal2) vê tudo, inclusive itens sem comunidade e a rede toda', async () => {
  await como(U.farley, 'aal2');
  assert.equal((await sql('select * from snapshots')).length, 3);
  assert.equal((await sql('select * from moderacao')).length, 5);
  const eq = (await um('select rnq_equipe_listar() as e')).e;
  assert.equal(eq.length, 3);
  assert.equal(eq.find(x => x.email === 'farley@exemplo.org').mfa, true);
  assert.equal((await sql('select * from auditoria')).length > 0, true);
});

test('tecelão que cadastrou MFA precisa entrar com o código (aal2)', async () => {
  await dono();
  await sql("insert into auth.mfa_factors (user_id, status) values ($1, 'verified')", [U.tecB]);
  await como(U.tecB, 'aal1');
  assert.equal((await sql('select * from snapshots')).length, 0);
  await como(U.tecB, 'aal2');
  assert.deepEqual((await sql('select escopo from snapshots')).map(r => r.escopo), ['esg']);
});

test('CA27: tecelão não muda o próprio papel nem as comunidades', async () => {
  await como(U.tecA, 'aal2');
  await falha(sql("select rnq_equipe_atualizar($1, 'admin', null, null, null)", [U.tecA]), 'só admin');
  await falha(sql("select rnq_equipe_atualizar($1, null, null, '{esg}', null)", [U.tecA]), 'só admin');
  await falha(sql("update equipe set papel = 'admin' where user_id = $1", [U.tecA]), 'permission denied');
  await falha(sql("insert into equipe_comunidades values ($1, 'esg')", [U.tecA]), 'permission denied');
  await falha(sql("select rnq_convite_registrar($1, 'x@x', 'x', 'admin', '{}', 'pt', null)", [U.fora]), 'permission denied');
});

test('admin atribui comunidades e o recorte muda na hora', async () => {
  await como(U.farley, 'aal2');
  await sql("select rnq_equipe_atualizar($1, null, null, '{tecnologia,teoria-u}', null)", [U.tecA]);
  await falha(sql("select rnq_equipe_atualizar($1, null, null, '{inexistente}', null)", [U.tecA]), 'desconhecida');
  await como(U.tecA);
  assert.deepEqual((await um('select rnq_meu_perfil() as p')).p.comunidades, ['tecnologia', 'teoria-u']);
});

test('CA28: o último admin ativo não pode ser rebaixado nem desativado', async () => {
  await como(U.farley, 'aal2');
  await falha(sql("select rnq_equipe_atualizar($1, 'tecelao', null, null, null)", [U.farley]), 'pelo menos um admin');
  await falha(sql("select rnq_equipe_atualizar($1, null, false, null, null)", [U.farley]), 'pelo menos um admin');
  await servico();                                                  // nem a chave secreta consegue
  await falha(sql("update equipe set ativo = false where user_id = $1", [U.farley]), 'pelo menos um admin');
  await falha(sql("delete from equipe where user_id = $1", [U.farley]), 'pelo menos um admin');
});

test('com um segundo admin, o primeiro pode deixar de ser admin', async () => {
  await dono();
  await sql("insert into auth.mfa_factors (user_id, status) values ($1, 'verified')", [U.june]);
  await servico();
  await sql("select rnq_convite_registrar($1, 'june@exemplo.org', 'June', 'admin', '{}', 'en', $2)", [U.june, U.farley]);
  await como(U.june, 'aal2');
  const r = (await um("select rnq_equipe_atualizar($1, 'tecelao', null, null, null) as r", [U.farley])).r;
  assert.equal(r.papel, 'tecelao');
  await sql("select rnq_equipe_atualizar($1, 'admin', null, null, null)", [U.farley]);   // volta
});

test('RF29: desativar corta o acesso na hora e apaga as sessões', async () => {
  await dono();
  await sql('insert into auth.sessions (user_id) values ($1), ($1)', [U.tecA]);
  await como(U.farley, 'aal2');
  await sql("select rnq_equipe_atualizar($1, null, false, null, null)", [U.tecA]);
  await dono();
  assert.equal((await sql('select * from auth.sessions where user_id = $1', [U.tecA])).length, 0);
  await como(U.tecA);
  assert.equal((await um('select rnq_meu_perfil() as p')).p, null);
  assert.equal((await sql('select * from snapshots')).length, 0);
  assert.equal((await sql('select * from moderacao')).length, 0);
  await como(U.farley, 'aal2');
  await sql("select rnq_equipe_atualizar($1, null, true, null, null)", [U.tecA]);           // reativa
  await como(U.tecA);
  assert.equal((await sql('select * from snapshots')).length, 1);
});

test('RF23: a auditoria não pode ser alterada nem apagada (nem pela chave secreta)', async () => {
  await como(U.farley, 'aal2');
  await falha(sql('delete from auditoria'), 'permission denied');
  await falha(sql("insert into auditoria (acao) values ('falsa')"), 'permission denied');
  await servico();
  await falha(sql("update auditoria set acao = 'x'"), 'não pode ser alterada');
  await falha(sql('delete from auditoria'), 'não pode ser alterada');
  const acoes = (await sql('select distinct acao from auditoria order by acao')).map(r => r.acao);
  for (const a of ['equipe.atualizar', 'equipe.convidar', 'moderacao.decidir', 'pipeline.sincronizar']) {
    assert.ok(acoes.includes(a), `faltou ${a} na auditoria`);
  }
});

test('o navegador nunca escreve direto nas tabelas', async () => {
  await como(U.farley, 'aal2');
  await falha(sql("insert into moderacao (tipo, item_id) values ('mural', 'x')"), 'permission denied');
  await falha(sql("delete from snapshots"), 'permission denied');
  await falha(sql("update comunidades set nome = 'x'"), 'permission denied');
});

test('funções do pipeline só com a chave secreta', async () => {
  for (const entrar of [() => como(U.farley, 'aal2'), anonimo]) {
    await entrar();
    await falha(sql("select rnq_pipeline_sincronizar('{}'::jsonb)"), 'permission denied');
    await falha(sql('select rnq_pipeline_decisoes()'), 'permission denied');
    await falha(sql('select rnq_pipeline_status()'), 'permission denied');
    await falha(sql("select rnq_usuario_por_email('farley@exemplo.org')"), 'permission denied');
  }
  await servico();
  assert.equal((await um("select rnq_usuario_por_email('FARLEY@exemplo.org ') as u")).u, U.farley);
  const st = (await um('select rnq_pipeline_status() as s')).s;
  assert.equal(st.admins, 2);
});

test('D5: decisão do painel vence a planilha; item que sumiu é apagado; snapshot substituído', async () => {
  await servico();
  const ini = await um("select status, origem_decisao from moderacao where item_id = 'i-ja'");
  assert.deepEqual(ini, { status: 'aprovado', origem_decisao: 'planilha' });   // migração única
  const esg = (await um("select id from moderacao where item_id = 'c-esg'")).id;
  await como(U.farley, 'aal2');
  await sql("select rnq_decidir($1, 'recusado', 'duplicado')", [esg]);
  await servico();
  const itens = ITENS.filter(i => i.item_id !== 'p-sem')
    .map(i => i.item_id === 'c-esg' ? { ...i, status_planilha: 'aprovado', titulo: 'Bruno ESG (editado)' } : i);
  const r = (await sincronizar(itens, SNAPS.filter(s => s.escopo !== 'esg'))).r;
  assert.equal(r.itens_apagados, 1);
  assert.equal(r.itens_novos, 0);
  const c = await um("select status, titulo, motivo from moderacao where item_id = 'c-esg'");
  assert.deepEqual(c, { status: 'recusado', titulo: 'Bruno ESG (editado)', motivo: 'duplicado' });
  assert.equal((await sql("select * from moderacao where item_id = 'p-sem'")).length, 0);
  assert.deepEqual((await sql('select escopo from snapshots order by escopo')).map(x => x.escopo), ['rede', 'tecnologia']);
  const dec = (await um('select rnq_pipeline_decisoes() as d')).d;
  assert.equal(dec.find(d => d.item_id === 'c-esg').status, 'recusado');
});

test('comunidade que some fica inativa, sem perder quem tece nela', async () => {
  await servico();
  await sincronizar(ITENS, SNAPS, COMS.filter(c => c.id !== 'teoria-u'));
  assert.equal((await um("select ativa from comunidades where id = 'teoria-u'")).ativa, false);
  assert.equal((await sql("select * from equipe_comunidades where comunidade_id = 'teoria-u'")).length, 1);
  await sincronizar();
  assert.equal((await um("select ativa from comunidades where id = 'teoria-u'")).ativa, true);
});

test('sincronização com formato inválido é recusada sem mudar nada', async () => {
  await servico();
  const antes = (await um('select count(*)::int n from moderacao')).n;
  await falha(sql("select rnq_pipeline_sincronizar('{\"itens\": 3}'::jsonb)"), 'inválido');
  assert.equal((await um('select count(*)::int n from moderacao')).n, antes);
});

test('idioma: cada pessoa muda só o próprio', async () => {
  await como(U.tecB, 'aal2');
  await sql("select rnq_definir_idioma('pt')");
  await falha(sql("select rnq_definir_idioma('fr')"), 'inválido');
  assert.equal((await um('select rnq_meu_perfil() as p')).p.idioma, 'pt');
});

test('RF26: cadastro de quem escolheu ficar fora do mapa não pode ser aprovado', async () => {
  await servico();
  const id = (await um("select id from moderacao where item_id = 'c-fora'")).id;
  await como(U.farley, 'aal2');
  await falha(sql("select rnq_decidir($1, 'aprovado', null)", [id]), 'não pode ser aprovado');
  const r = await um("select (rnq_decidir($1, 'recusado', 'escolheu ficar fora')).status", [id]);
  assert.equal(r.status, 'recusado');
});

test('envio que chega na hora pelo site: entra pendente, não duplica e herda comunidades', async () => {
  await servico();
  const r = (await um("select rnq_receber_envio($1::jsonb) as r", [JSON.stringify({ itens: [
    { tipo: 'mural', item_id: 'site-1', comunidades: ['esg'], titulo: 'Pedido: ajuda', conteudo: { campos: [] },
      privado: { campos: [['Contato (privado)', 'x@site.org']] }, recebido_em: '2026-10-16T16:13:00-03:00' },
    { tipo: 'resposta', item_id: 'site-2', comunidades: [], ref: 'site-1', titulo: 'Ana → ajuda' },
    { tipo: 'mural', item_id: 'm-tec', comunidades: [], titulo: 'NÃO pode sobrescrever' },
  ] })])).r;
  assert.equal(r.novos, 2);
  const s1 = await um("select status, fonte, comunidades from moderacao where item_id = 'site-1'");
  assert.deepEqual(s1, { status: 'pendente', fonte: 'site', comunidades: ['esg'] });
  assert.deepEqual((await um("select comunidades from moderacao where item_id = 'site-2'")).comunidades, ['esg']);
  assert.notEqual((await um("select titulo from moderacao where item_id = 'm-tec'")).titulo, 'NÃO pode sobrescrever');
  assert.ok((await sql("select * from auditoria where acao = 'site.envio'")).length >= 2);
  // tecelão de ESG vê na hora; de fora, não
  await como(U.tecB, 'aal2');
  assert.ok((await sql("select * from moderacao where item_id = 'site-1'")).length === 1);
  await como(U.tecA);
  assert.equal((await sql("select * from moderacao where item_id = 'site-1'")).length, 0);
});

test('a sincronização do Mac não apaga o que acabou de chegar pelo site; depois assume o item', async () => {
  await servico();
  await sincronizar();                                   // planilha ainda sem site-1
  assert.equal((await sql("select * from moderacao where item_id = 'site-1'")).length, 1);
  const item = { tipo: 'mural', item_id: 'site-1', comunidades: ['esg', 'tecnologia'], titulo: 'Pedido: ajuda',
                 conteudo: {}, privado: {}, status_planilha: 'pendente' };
  await sincronizar([...ITENS, item]);
  assert.deepEqual(await um("select fonte, comunidades from moderacao where item_id = 'site-1'"),
                   { fonte: 'planilha', comunidades: ['esg', 'tecnologia'] });
  await sincronizar();                                   // saiu da planilha: agora pode apagar
  assert.equal((await sql("select * from moderacao where item_id = 'site-1'")).length, 0);
});

test('envio do site só com a chave secreta; formato inválido recusado', async () => {
  for (const entrar of [() => como(U.farley, 'aal2'), anonimo]) {
    await entrar();
    await falha(sql("select rnq_receber_envio('{\"itens\":[]}'::jsonb)"), 'permission denied');
    await falha(sql("select rnq_pipeline_registrar('ultima_publicacao', '{}'::jsonb)"), 'permission denied');
  }
  await servico();
  await falha(sql("select rnq_receber_envio('{\"itens\": 1}'::jsonb)"), 'inválido');
  await falha(sql("select rnq_pipeline_registrar('qualquer', '{}'::jsonb)"), 'inválida');
});

test('status do painel: última publicação e rotina diária, só para a equipe', async () => {
  await servico();
  await sql("select rnq_pipeline_registrar('ultima_publicacao', $1::jsonb)", [JSON.stringify({ quando: '2026-10-17T07:01:00-03:00', ok: true })]);
  await sql("select rnq_pipeline_registrar('rotina_diaria', $1::jsonb)", [JSON.stringify({ hora: '07:00', ligada: true })]);
  await como(U.tecB, 'aal2');
  const s = (await um('select rnq_painel_status() as s')).s;
  assert.equal(s.ultima_publicacao.ok, true);
  assert.equal(s.rotina_diaria.hora, '07:00');
  assert.ok(s.ultima_atualizacao);
  await como(U.fora, 'aal2');
  assert.equal((await um('select rnq_painel_status() as s')).s, null);
});
