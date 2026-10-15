// Testes da Edge Function "convidar" (admin/supabase/functions/convidar/logica.js), com clientes falsos.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { tratarConvite, validar } from '../../admin/supabase/functions/convidar/logica.js';

const ENV = { SUPABASE_URL: 'https://x.supabase.co', SUPABASE_ANON_KEY: 'anon', SUPABASE_SERVICE_ROLE_KEY: 'servico',
              RNQ_PAINEL_URL: 'https://painel-novoquilombo.netlify.app' };
const ORIGEM = 'https://painel-novoquilombo.netlify.app';

function fabrica({ admin = true, usuario = 'u-admin', existente = null, erroConvite = null } = {}) {
  const chamadas = [];
  const criarCliente = (url, chave, opcoes) => {
    const ehServico = chave === 'servico';
    return {
      auth: {
        getUser: async () => (usuario ? { data: { user: { id: usuario } }, error: null } : { data: null, error: { message: 'x' } }),
        admin: {
          inviteUserByEmail: async (email, o) => {
            chamadas.push(['convite', email, o]);
            return erroConvite ? { data: null, error: { message: erroConvite } } : { data: { user: { id: 'u-novo' } }, error: null };
          },
        },
      },
      rpc: async (nome, args) => {
        chamadas.push([ehServico ? 'servico' : 'pessoa', nome, args, opcoes]);
        if (nome === 'rnq_eh_admin') return { data: admin, error: null };
        if (nome === 'rnq_usuario_por_email') return { data: existente, error: null };
        if (nome === 'rnq_convite_registrar') return { data: { novo: !existente }, error: null };
        return { data: null, error: { message: 'função inesperada' } };
      },
    };
  };
  return { criarCliente, chamadas };
}
const pedir = (f, extra = {}) => tratarConvite({ metodo: 'POST', origem: ORIGEM, autorizacao: 'Bearer jwt-da-pessoa',
  corpo: { email: 'Nova@Exemplo.org ', nome: 'Nova', papel: 'tecelao', comunidades: ['tecnologia'], idioma: 'pt' },
  env: ENV, criarCliente: f.criarCliente, ...extra });

test('admin convida: confere admin com o login de quem chama e registra com a chave de serviço', async () => {
  const f = fabrica();
  const r = await pedir(f);
  assert.equal(r.status, 200);
  assert.deepEqual(r.json, { ok: true, novo: true, convite_enviado: true });
  const adm = f.chamadas.find(c => c[1] === 'rnq_eh_admin');
  assert.equal(adm[0], 'pessoa');
  assert.equal(adm[3].global.headers.Authorization, 'Bearer jwt-da-pessoa');
  const conv = f.chamadas.find(c => c[0] === 'convite');
  assert.equal(conv[1], 'nova@exemplo.org');
  assert.equal(conv[2].redirectTo, ORIGEM);
  const reg = f.chamadas.find(c => c[1] === 'rnq_convite_registrar');
  assert.equal(reg[0], 'servico');
  assert.equal(reg[2].p_convidado_por, 'u-admin');
  assert.equal(r.headers['Access-Control-Allow-Origin'], ORIGEM);
});

test('quem não é admin (ou está sem MFA) recebe 403 e nada é convidado', async () => {
  const f = fabrica({ admin: false });
  const r = await pedir(f);
  assert.equal(r.status, 403);
  assert.ok(!f.chamadas.some(c => c[0] === 'convite' || c[1] === 'rnq_convite_registrar'));
});

test('sem login: 401', async () => {
  assert.equal((await pedir(fabrica(), { autorizacao: null })).status, 401);
  assert.equal((await pedir(fabrica({ usuario: null }))).status, 401);
});

test('outra origem: 403; OPTIONS: 204; GET: 405', async () => {
  assert.equal((await pedir(fabrica(), { origem: 'https://malicioso.example' })).status, 403);
  assert.equal((await pedir(fabrica(), { metodo: 'OPTIONS' })).status, 204);
  assert.equal((await pedir(fabrica(), { metodo: 'GET' })).status, 405);
});

test('quem já tem conta não recebe outro e-mail: só o acesso é atualizado', async () => {
  const f = fabrica({ existente: 'u-velho' });
  const r = await pedir(f);
  assert.equal(r.status, 200);
  assert.equal(r.json.novo, false);
  assert.equal(r.json.convite_enviado, false);
  assert.ok(!f.chamadas.some(c => c[0] === 'convite'));
});

test('falha de e-mail (sem SMTP próprio) vira erro claro', async () => {
  const r = await pedir(fabrica({ erroConvite: 'Email address not authorized' }));
  assert.equal(r.status, 502);
  assert.equal(r.json.codigo, 'smtp');
});

test('sem chaves configuradas: erro claro, nada é chamado', async () => {
  const f = fabrica();
  const r = await tratarConvite({ metodo: 'POST', origem: ORIGEM, autorizacao: 'Bearer x', corpo: {},
    env: { SUPABASE_URL: 'https://x', RNQ_PAINEL_URL: ORIGEM }, criarCliente: f.criarCliente });
  assert.equal(r.status, 500);
  assert.equal(f.chamadas.length, 0);
});

test('chaves novas (segredos RNQ_CHAVE_*) servem quando as antigas estão desligadas', async () => {
  const f = fabrica();
  const env = { SUPABASE_URL: 'https://x', RNQ_PAINEL_URL: ORIGEM, RNQ_CHAVE_PUBLICA: 'sb_publishable_1', RNQ_CHAVE_SECRETA: 'servico' };
  const r = await tratarConvite({ metodo: 'POST', origem: ORIGEM, autorizacao: 'Bearer jwt', env, criarCliente: f.criarCliente,
    corpo: { email: 'a@b.org', papel: 'admin' } });
  assert.equal(r.status, 200);
});

test('validação do pedido', () => {
  const ok = { email: 'a@b.org', papel: 'tecelao', comunidades: ['esg'] };
  assert.equal(validar(ok), null);
  assert.match(validar({ ...ok, email: 'x' }), /E-mail/);
  assert.match(validar({ ...ok, papel: 'dono' }), /Papel/);
  assert.match(validar({ ...ok, comunidades: [] }), /comunidade/);
  assert.match(validar({ ...ok, comunidades: ['<script>'] }), /Comunidades/);
  assert.equal(validar({ email: 'a@b.org', papel: 'admin' }), null);
  assert.match(validar({ ...ok, idioma: 'fr' }), /Idioma/);
});
