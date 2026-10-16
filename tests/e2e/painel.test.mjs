// Testes de ponta a ponta do painel admin (admin/), num Chromium de verdade, servido com a mesma
// Content-Security-Policy do Netlify (admin/_headers).
//  - modo demonstração: visão da rede, moderação, equipe, histórico, "ver como" tecelã, PT/EN, celular;
//  - modo real com um Supabase falso: login por código, MFA (cadastro e desafio), sem convite, convite.
// Uso: node --test tests/e2e/painel.test.mjs   (ou npm run test:painel)
import { test, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { servir } from './servidor.mjs';
import { supabaseFalso, lerDemo, URL_FALSA } from './supabase-falso.mjs';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const ADMIN = path.join(RAIZ, 'admin');
const FOTOS = path.join(RAIZ, 'tests', 'e2e', 'screenshots');
fs.mkdirSync(FOTOS, { recursive: true });

let browser, demo, real;
const CFG_REAL = `window.RNQ_PAINEL_CONFIG = ${JSON.stringify({ supabaseUrl: URL_FALSA, chavePublica: 'sb_publishable_teste' })};`;

before(async () => {
  const opcoes = {};
  if (process.env.CHROMIUM_PATH) opcoes.executablePath = process.env.CHROMIUM_PATH;
  else if (fs.existsSync('/opt/pw-browsers/chromium')) opcoes.executablePath = '/opt/pw-browsers/chromium';
  browser = await chromium.launch(opcoes);
  demo = await servir(ADMIN, { extras: { 'config.js': 'window.RNQ_PAINEL_CONFIG = null;' } });
  real = await servir(ADMIN, { extras: { 'config.js': CFG_REAL } });
});
after(async () => { await browser.close(); demo.srv.close(); real.srv.close(); });

async function abrir(base, { w = 1400, h = 900, locale = 'pt-BR', busca = '', antes } = {}) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, locale });
  await ctx.grantPermissions(['clipboard-read', 'clipboard-write'], { origin: base });
  const p = await ctx.newPage();
  p.erros = [];
  p.on('pageerror', e => p.erros.push(e.message));
  p.on('console', m => { if (m.type() === 'error' || /Content.Security.Policy/i.test(m.text())) p.erros.push(m.text()); });
  if (antes) await antes(p);
  await p.goto(base + '/' + busca);
  await p.waitForFunction(() => window.RNQ_PRONTO === true);
  return p;
}
const fechar = (p) => p.context().close();
const aba = (p, id) => p.click(`[data-aba=${id}]`);
const semRolagemHorizontal = (p) => p.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);

// ------------------------------------------------------------------------------- demonstração
test('demo abre na visão da rede toda, sem erros nem bloqueios da CSP', async () => {
  const p = await abrir(demo.url);
  assert.equal(await p.textContent('#conteudo h2'), 'Rede toda');
  assert.ok(await p.locator('.demo-faixa').isVisible());
  const frame = p.frameLocator('iframe.visao');
  await frame.locator('text=Saúde da rede').waitFor();
  // o script do iframe (com hash na CSP) manda a altura: prova que a CSP deixa só ele rodar
  await p.waitForFunction(() => parseInt(document.querySelector('iframe.visao').style.height || '0', 10) > 1500);
  assert.deepEqual(p.erros, []);
  await p.screenshot({ path: path.join(FOTOS, 'painel-01-visao.png') });
  await fechar(p);
});

test('o iframe da visão é isolado: sem acesso à página do painel', async () => {
  const p = await abrir(demo.url);
  assert.equal(await p.getAttribute('iframe.visao', 'sandbox'), 'allow-scripts');
  const frame = p.frames().find(f => f !== p.mainFrame());
  await p.frameLocator('iframe.visao').locator('h2').first().waitFor();
  const acesso = await frame.evaluate(() => { try { return !!parent.document.body; } catch (_) { return 'bloqueado'; } });
  assert.equal(acesso, 'bloqueado');
  const armazenamento = await frame.evaluate(() => { try { localStorage.length; return 'livre'; } catch (_) { return 'bloqueado'; } });
  assert.equal(armazenamento, 'bloqueado');
  await fechar(p);
});

test('copiar uma mensagem pronta no iframe copia de verdade (via página do painel)', async () => {
  const p = await abrir(demo.url);
  const frame = p.frameLocator('iframe.visao');
  await frame.locator('[data-copiar]').first().click();
  await p.locator('.toast', { hasText: 'Mensagem copiada' }).waitFor();
  const copiado = await p.evaluate(() => navigator.clipboard.readText());
  assert.match(copiado, /Quero apresentar vocês|Rede Novo Quilombo/);
  await fechar(p);
});

test('trocar de comunidade troca a visão e os números', async () => {
  const p = await abrir(demo.url);
  const antes = await p.textContent('.resumo div:first-child b');
  await p.click('[data-escopo=tecnologia]');
  assert.equal(await p.textContent('#conteudo h2'), 'Tecnologia');
  assert.notEqual(await p.textContent('.resumo div:first-child b'), antes);
  await p.frameLocator('iframe.visao').locator('text=não está nesta comunidade').waitFor();
  await fechar(p);
});

test('moderação: aprovar, recusar com motivo e desfazer', async () => {
  const p = await abrir(demo.url);
  await aba(p, 'moderacao');
  const pend = async () => Number(await p.textContent('[data-status=pendente] span.suave'));
  const n0 = await pend();
  const primeiro = p.locator('article.item').first();
  const id = await primeiro.getAttribute('data-id');
  await primeiro.locator('[data-acao=aprovar]').click();
  await p.locator('.toast', { hasText: 'Aprovado' }).waitFor();
  assert.equal(await pend(), n0 - 1);
  assert.equal(await p.locator(`article.item[data-id="${id}"]`).count(), 0, 'sai da lista de pendentes');

  const segundo = p.locator('article.item').first();
  const id2 = await segundo.getAttribute('data-id');
  await segundo.locator('[data-acao=recusar]').click();
  await p.fill(`#motivo-${id2}`, 'Duplicado');
  await p.click('[data-acao=confirmar-recusa]');
  await p.click('[data-status=recusado]');
  const recusado = p.locator(`article.item[data-id="${id2}"]`);
  assert.match(await recusado.textContent(), /Duplicado/);
  await recusado.locator('[data-acao=desfazer]').click();
  await p.click('[data-status=pendente]');
  assert.equal(await p.locator(`article.item[data-id="${id2}"]`).count(), 1);
  await aba(p, 'historico');
  assert.match(await p.textContent('ol.historico'), /Duplicado/);
  await fechar(p);
});

test('contatos ficam escondidos até pedir; cadastro de quem não quer aparecer não pode ser aprovado', async () => {
  const p = await abrir(demo.url);
  await aba(p, 'moderacao');
  const card = p.locator('article.item[data-tipo=mural]').first();
  assert.doesNotMatch(await card.textContent(), /@exemplo\.org/);
  await card.locator('[data-teste=privado]').click();
  assert.match(await p.locator('article.item[data-tipo=mural]').first().textContent(), /@exemplo\.org/);
  const igor = p.locator('article.item', { hasText: 'Igor Reservado' });
  assert.ok(await igor.locator('[data-acao=aprovar]').isDisabled());
  assert.match(await igor.textContent(), /escolheu não aparecer/);
  await p.screenshot({ path: path.join(FOTOS, 'painel-02-moderacao.png') });
  await fechar(p);
});

test('filtros por tipo, comunidade e busca', async () => {
  const p = await abrir(demo.url);
  await aba(p, 'moderacao');
  await p.click('[data-status=todos]');
  await p.selectOption('#f-tipo', 'cadastro');
  assert.equal(await p.locator('article.item').count(), 2);
  await p.selectOption('#f-tipo', '');
  await p.selectOption('#f-com', 'esg');
  const tipos = await p.locator('article.item').evaluateAll(els => els.length);
  assert.ok(tipos >= 1);
  await p.selectOption('#f-com', '');
  await p.fill('#f-busca', 'Helena');
  assert.equal(await p.locator('article.item').count(), 1);
  await fechar(p);
});

test('ver como tecelã: só as comunidades dela, sem equipe nem histórico', async () => {
  const p = await abrir(demo.url);
  const iara = await p.$eval('[data-teste=ver-como]', s => [...s.options].find(o => o.text.startsWith('Iara')).value);
  await p.selectOption('[data-teste=ver-como]', iara);
  await p.waitForFunction(() => document.querySelector('[data-teste=quem]').textContent.startsWith('Iara'));
  assert.equal(await p.locator('[data-aba=equipe]').count(), 0);
  assert.equal(await p.locator('[data-aba=historico]').count(), 0);
  const escopos = await p.$$eval('[data-escopo]', b => b.map(x => x.dataset.escopo).sort());
  assert.deepEqual(escopos, ['esg', 'tecnologia']);
  await aba(p, 'moderacao');
  await p.click('[data-status=todos]');
  const coms = await p.$$eval('article.item', els => els.map(e => e.querySelector('.chips')?.textContent || ''));
  assert.ok(coms.length > 0);
  assert.ok(coms.every(t => /Tecnologia|ESG/.test(t)), 'só itens de Tecnologia ou ESG');
  await fechar(p);
});

test('equipe: convidar exige comunidade para tecelão; o último admin não pode sair', async () => {
  const p = await abrir(demo.url);
  await aba(p, 'equipe');
  const antes = await p.locator('article.pessoa').count();
  await p.fill('#c-email', 'nova.tecela@exemplo.org');
  await p.fill('#c-nome', 'Nova Tecelã');
  await p.click('[data-teste=convite] button[type=submit]');
  assert.match(await p.textContent('[data-teste=convite] .msg'), /ao menos uma comunidade/);
  await p.check('[data-teste=convite] input[value=tecnologia]');
  await p.click('[data-teste=convite] button[type=submit]');
  await p.locator('.toast', { hasText: 'Convite enviado' }).waitFor();
  assert.equal(await p.locator('article.pessoa').count(), antes + 1);
  const eu = p.locator('article.pessoa').first();
  await eu.locator('[data-campo=papel]').selectOption('tecelao');
  await eu.locator('input[type=checkbox]').first().check();
  await eu.locator('[data-acao=salvar]').click();
  await p.locator('.toast', { hasText: 'pelo menos um admin' }).waitFor();
  await p.screenshot({ path: path.join(FOTOS, 'painel-03-equipe.png') });
  await fechar(p);
});

test('tirar o acesso de alguém pede confirmação e fica no histórico', async () => {
  const p = await abrir(demo.url);
  await aba(p, 'equipe');
  p.once('dialog', d => d.accept());
  const caio = p.locator('article.pessoa', { hasText: 'Caio' });
  await caio.locator('[data-acao=acesso]').click();
  await p.locator('article.pessoa[data-ativo=false]', { hasText: 'Caio' }).waitFor();
  await aba(p, 'historico');
  assert.match(await p.textContent('ol.historico'), /caio@exemplo\.org/);
  await fechar(p);
});

test('inglês: interface, visão e rótulos das colunas', async () => {
  const p = await abrir(demo.url, { busca: '?lang=en' });
  assert.equal(await p.textContent('#conteudo h2'), 'Whole network');
  await p.frameLocator('iframe.visao').locator('text=Network health').waitFor();
  await aba(p, 'moderacao');
  assert.match(await p.textContent('.filtros'), /Pending/);
  assert.match(await p.textContent('article.item[data-tipo=mural] dl'), /Description/);
  await p.click('[data-teste=idioma]');
  assert.equal(await p.textContent('[data-aba=moderacao]').then(t => t.replace(/\d+/g, '').trim()), 'Moderação');
  await fechar(p);
});

test('celular (390 px): nenhuma aba tem rolagem horizontal', async () => {
  const p = await abrir(demo.url, { w: 390, h: 844 });
  for (const id of ['visao', 'moderacao', 'equipe', 'historico']) {
    await aba(p, id);
    await p.waitForTimeout(150);
    assert.ok(await semRolagemHorizontal(p), `rolagem horizontal na aba ${id}`);
    await p.screenshot({ path: path.join(FOTOS, `painel-04-celular-${id}.png`) });
  }
  await fechar(p);
});

test('teclado: setas trocam de aba', async () => {
  const p = await abrir(demo.url);
  await p.focus('[data-aba=visao]');
  await p.keyboard.press('ArrowRight');
  assert.equal(await p.getAttribute('[data-aba=moderacao]', 'aria-selected'), 'true');
  await fechar(p);
});

test('PT e EN têm as mesmas chaves de texto', async () => {
  const vm = await import('node:vm');
  const caixa = { window: {} };
  vm.runInNewContext(fs.readFileSync(path.join(ADMIN, 'i18n.js'), 'utf8'), caixa);
  const { pt, en } = caixa.window.RNQ_I18N;
  const chaves = (o) => Object.keys(o).sort();
  assert.deepEqual(chaves(pt), chaves(en));
  for (const k of ['tipos', 'tipos_ajuda', 'bloqueio', 'acoes', 'feito_ok']) assert.deepEqual(chaves(pt[k]), chaves(en[k]), k);
});

// ------------------------------------------------------------------------------- modo real (Supabase falso)
const ADMIN_PERFIL = { user_id: 'u-1', email: 'farley@exemplo.org', nome: 'Farley', papel: 'admin', idioma: 'pt',
                       comunidades: [], mfa_exigido: true };

async function entrarComCodigo(p) {
  await p.fill('#email', 'Farley@Exemplo.org');
  await p.click('button[type=submit]');
  await p.locator('#codigo').waitFor();
  await p.fill('#codigo', '111111');
  await p.click('button[type=submit]');
  await p.locator('.msg.erro', { hasText: 'Código errado' }).waitFor();
  await p.fill('#codigo', '123456');
  await p.click('button[type=submit]');
}

test('real: só convidados (shouldCreateUser: false), código errado avisa, admin cadastra o MFA e entra', async () => {
  const dados = lerDemo(RAIZ);
  let est;
  const p = await abrir(real.url, { antes: async (pg) => { est = await supabaseFalso(pg, { dados, perfil: ADMIN_PERFIL }); } });
  assert.equal(await p.textContent('h1'), 'Painel da tecelagem');
  await p.screenshot({ path: path.join(FOTOS, 'painel-00-entrar.png') });
  await entrarComCodigo(p);
  const otp = est.pedidos.find(x => x.caminho === '/auth/v1/otp');
  assert.equal(otp.corpo.email, 'farley@exemplo.org');
  assert.equal(otp.corpo.create_user, false);
  await p.locator('.qr img').waitFor();
  assert.match(await p.textContent('.segredo'), /JBSWY3DPEHPK3PXP/);
  await p.fill('#mfa', '000000');
  await p.click('button[type=submit]');
  await p.locator('.msg.erro').waitFor();
  await p.fill('#mfa', '654321');
  await p.click('button[type=submit]');
  await p.locator('[data-teste=quem]', { hasText: 'Farley' }).waitFor();
  assert.ok(await p.locator('[data-aba=equipe]').isVisible());
  await p.frameLocator('iframe.visao').locator('text=Saúde da rede').waitFor();
  // dados pedidos com a sessão aal2
  const rest = est.pedidos.filter(x => x.caminho.startsWith('/rest/v1/snapshots'));
  assert.ok(rest.length >= 1);
  const tok = rest.at(-1).auth.replace('Bearer ', '').split('.')[1];
  assert.equal(JSON.parse(Buffer.from(tok, 'base64url').toString()).aal, 'aal2');
  // (os códigos errados de propósito geram 403/422 no console; nada além disso)
  assert.deepEqual(p.erros.filter(e => !e.startsWith('Failed to load resource')), []);
  await fechar(p);
});

test('real: admin com MFA já cadastrado só digita o código; decide e convida pelo banco', async () => {
  const dados = lerDemo(RAIZ);
  let est;
  const p = await abrir(real.url, { antes: async (pg) => { est = await supabaseFalso(pg, { dados, perfil: ADMIN_PERFIL, fatorVerificado: true }); } });
  await entrarComCodigo(p);
  await p.locator('#mfa').waitFor();
  assert.equal(await p.locator('.qr').count(), 0);
  await p.fill('#mfa', '654321');
  await p.click('button[type=submit]');
  await p.locator('[data-teste=quem]').waitFor();
  await aba(p, 'moderacao');
  const item = p.locator('article.item').first();
  const id = Number(await item.getAttribute('data-id'));
  await item.locator('[data-acao=aprovar]').click();
  await p.locator('.toast', { hasText: 'Aprovado' }).waitFor();
  const dec = est.pedidos.find(x => x.caminho === '/rest/v1/rpc/rnq_decidir');
  assert.deepEqual(dec.corpo, { p_id: id, p_status: 'aprovado', p_motivo: null });
  await aba(p, 'equipe');
  await p.fill('#c-email', 'june@exemplo.org');
  await p.selectOption('#c-papel', 'admin');
  await p.click('[data-teste=convite] button[type=submit]');
  await p.locator('.toast', { hasText: 'Convite enviado' }).waitFor();
  const conv = est.pedidos.find(x => x.caminho === '/functions/v1/convidar');
  assert.deepEqual(conv.corpo, { email: 'june@exemplo.org', nome: '', papel: 'admin', comunidades: [], idioma: 'pt' });
  assert.match(conv.auth, /^Bearer ey/);
  await fechar(p);
});

test('real: tecelã sem MFA entra direto e não vê a equipe', async () => {
  const dados = lerDemo(RAIZ);
  const perfil = { user_id: 'u-1', email: 'iara@exemplo.org', nome: 'Iara', papel: 'tecelao', idioma: 'en',
                   comunidades: ['tecnologia'], mfa_exigido: false };
  const p = await abrir(real.url, { antes: async (pg) => { await supabaseFalso(pg, { dados, perfil }); } });
  await entrarComCodigo(p);
  await p.locator('[data-teste=quem]', { hasText: 'Iara' }).waitFor();
  assert.equal(await p.locator('[data-aba=equipe]').count(), 0);
  assert.equal(await p.textContent('[data-aba=visao]'), 'Network view', 'usa o idioma do perfil');
  await fechar(p);
});

test('real: quem tem login mas não foi convidado vê a explicação', async () => {
  const dados = lerDemo(RAIZ);
  const p = await abrir(real.url, { antes: async (pg) => { await supabaseFalso(pg, { dados, perfil: null }); } });
  await entrarComCodigo(p);
  await p.locator('h1', { hasText: 'ainda não tem acesso' }).waitFor();
  await fechar(p);
});

test('real: entrar pelo link do e-mail (e-mail padrão do Supabase, sem código)', async () => {
  const dados = lerDemo(RAIZ);
  const perfil = { user_id: 'u-1', email: 'iara@exemplo.org', nome: 'Iara', papel: 'tecelao', idioma: 'pt',
                   comunidades: ['tecnologia'], mfa_exigido: false };
  const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
  const agora = Math.floor(Date.now() / 1000);
  const tok = `${b64({ alg: 'HS256' })}.${b64({ sub: 'u-1', email: perfil.email, role: 'authenticated', aal: 'aal1', exp: agora + 3600, iat: agora })}.x`;
  const hash = `#access_token=${tok}&expires_at=${agora + 3600}&expires_in=3600&refresh_token=r1&token_type=bearer&type=magiclink`;
  const ctx = await browser.newContext({ viewport: { width: 1200, height: 800 }, locale: 'pt-BR' });
  const p = await ctx.newPage();
  const est = await supabaseFalso(p, { dados, perfil });
  est.aal = 'aal1';
  await p.goto(real.url + '/' + hash);
  await p.waitForFunction(() => window.RNQ_PRONTO === true);
  await p.locator('[data-teste=quem]', { hasText: 'Iara' }).waitFor();
  assert.ok(!(await p.evaluate(() => location.hash)).includes('access_token'), 'o token sai do endereço');
  await ctx.close();
});
