// Integração da Edge Function "convidar" rodando de verdade no Deno (como no Supabase), contra um Supabase falso
// local. Opcional: só roda se houver Deno (DENO=/caminho/do/deno ou "deno" no PATH); sem Deno, é pulado.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import path from 'node:path';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const DENO = process.env.DENO || 'deno';
const temDeno = spawnSync(DENO, ['--version']).status === 0;

test('Edge Function no Deno: confere admin com o login da pessoa e convida com a chave de serviço', { skip: !temDeno && 'sem Deno' }, async () => {
  const pedidos = [];
  const falso = http.createServer((req, res) => {
    let corpo = '';
    req.on('data', c => { corpo += c; });
    req.on('end', () => {
      pedidos.push({ metodo: req.method, url: req.url, auth: req.headers.authorization, apikey: req.headers.apikey, corpo });
      const enviar = (s, j) => { res.writeHead(s, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(j)); };
      if (req.url.startsWith('/auth/v1/user')) return enviar(200, { id: 'u-admin', email: 'farley@exemplo.org', aud: 'authenticated' });
      if (req.url === '/rest/v1/rpc/rnq_eh_admin') return enviar(200, req.headers.authorization === 'Bearer jwt-da-pessoa');
      if (req.url === '/rest/v1/rpc/rnq_usuario_por_email') return enviar(200, null);
      if (req.url.startsWith('/auth/v1/invite')) return enviar(200, { id: 'u-novo', email: JSON.parse(corpo).email });
      if (req.url === '/rest/v1/rpc/rnq_convite_registrar') return enviar(200, { user_id: 'u-novo', novo: true });
      enviar(404, { message: 'rota desconhecida ' + req.url });
    });
  });
  await new Promise(ok => falso.listen(0, '127.0.0.1', ok));
  const base = `http://127.0.0.1:${falso.address().port}`;
  const funcao = spawn(DENO, ['run', '--allow-net', '--allow-env', '--allow-read',
    path.join(RAIZ, 'admin', 'supabase', 'functions', 'convidar', 'index.ts')], {
    env: { ...process.env, SUPABASE_URL: base, SUPABASE_ANON_KEY: 'anon', SUPABASE_SERVICE_ROLE_KEY: 'chave-servico',
           RNQ_PAINEL_URL: 'https://painel-novoquilombo.netlify.app', DENO_NO_UPDATE_CHECK: '1',
           NO_PROXY: '127.0.0.1,localhost', no_proxy: '127.0.0.1,localhost' },
    stdio: ['ignore', 'pipe', 'pipe'], detached: true });
  let log = '';
  funcao.stdout.on('data', d => { log += d; });
  funcao.stderr.on('data', d => { log += d; });
  try {
    const url = await new Promise((ok, falha) => {
      const t = setTimeout(() => falha(new Error('Deno não subiu: ' + log)), 120000);
      const olhar = setInterval(() => {
        const m = log.match(/https?:\/\/[^\s]+:(\d+)\//);
        if (m) { clearInterval(olhar); clearTimeout(t); ok(`http://127.0.0.1:${m[1]}/`); }
      }, 100);
    });
    const r = await fetch(url, { method: 'POST', headers: { Authorization: 'Bearer jwt-da-pessoa', Origin: 'https://painel-novoquilombo.netlify.app',
      'Content-Type': 'application/json' }, body: JSON.stringify({ email: 'nova@exemplo.org', papel: 'tecelao', comunidades: ['esg'] }),
      signal: AbortSignal.timeout(60000) });
    assert.equal(r.status, 200, log);
    assert.deepEqual(await r.json(), { ok: true, novo: true, convite_enviado: true });
    assert.equal(r.headers.get('access-control-allow-origin'), 'https://painel-novoquilombo.netlify.app');
    const convite = pedidos.find(p => p.url.startsWith('/auth/v1/invite'));
    assert.equal(convite.apikey, 'chave-servico');
    const adm = pedidos.find(p => p.url === '/rest/v1/rpc/rnq_eh_admin');
    assert.equal(adm.auth, 'Bearer jwt-da-pessoa');
    const negado = await fetch(url, { method: 'POST', headers: { Authorization: 'Bearer outro', 'Content-Type': 'application/json',
      Origin: 'https://painel-novoquilombo.netlify.app' }, body: '{}', signal: AbortSignal.timeout(60000) });
    assert.equal(negado.status, 403);
  } finally {
    try { process.kill(-funcao.pid, 'SIGKILL'); } catch (_) { funcao.kill('SIGKILL'); }
    funcao.stdout.destroy();
    funcao.stderr.destroy();
    falso.closeAllConnections();
    falso.close();
  }
});
