// Teste de ponta a ponta do site (abre o index.html num navegador de verdade).
// Uso: npm install && npm run test:e2e
// O site usa as bibliotecas de site/vendor (sem CDN), então o teste funciona offline.
import { chromium } from 'playwright';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import fs from 'node:fs';
import assert from 'node:assert/strict';

const RAIZ = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const SITE = path.join(RAIZ, 'site', 'index.html');
const FOTOS = path.join(RAIZ, 'tests', 'e2e', 'screenshots');
fs.mkdirSync(FOTOS, { recursive: true });
const nm = p => path.join(RAIZ, 'node_modules', p);

const opcoes = { args: ['--use-gl=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist'] };
if (process.env.CHROMIUM_PATH) opcoes.executablePath = process.env.CHROMIUM_PATH;
else if (fs.existsSync('/opt/pw-browsers/chromium')) opcoes.executablePath = '/opt/pw-browsers/chromium';
const browser = await chromium.launch(opcoes);

let falhas = 0, ok = 0;
async function teste(nome, fn) {
  try { await fn(); ok++; console.log('  ✓', nome); }
  catch (e) { falhas++; console.log('  ✗', nome, '\n    ', e.message.split('\n')[0]); }
}
async function pagina({ w = 1400, h = 860, query = '', hash = '', locale = 'pt-BR' } = {}) {
  const p = await browser.newPage({ viewport: { width: w, height: h }, locale });
  p.erros = [];
  p.on('pageerror', e => p.erros.push(e.message));
  await p.route('**fonts.g*/**', r => r.abort());
  await p.goto('file://' + SITE + query + hash);
  await p.waitForFunction(() => window.RNQ_APP);
  return p;
}

console.log('Site (e2e)');
const DADOS = JSON.parse(fs.readFileSync(path.join(RAIZ, 'site', 'rnq-publico.json'), 'utf8'));

await teste('carrega o mapa de pessoas sem erros de JavaScript', async () => {
  const p = await pagina();
  await p.waitForTimeout(2500);
  const nos = await p.locator('#vPessoas svg path').count();
  assert.ok(nos >= DADOS.pessoas.length, `esperava ≥ ${DADOS.pessoas.length} nós, achei ${nos}`);
  assert.deepEqual(p.erros, []);
  await p.waitForTimeout(5000); await p.screenshot({ path: path.join(FOTOS, '01-pessoas.png') });
  await p.close();
});

await teste('agrupar por Temas e Atuação troca título e legenda', async () => {
  const p = await pagina();
  await p.click('#seg button[data-d="temas"]');
  assert.equal(await p.textContent('#dimtitle'), 'Temas');
  assert.ok(await p.locator('#coms .com').count() >= 5);
  await p.click('#seg button[data-d="atuacao"]');
  assert.equal(await p.textContent('#dimtitle'), 'Atuação');
  await p.close();
});

await teste('card da pessoa mostra blocos e "Pode ser bom conhecer"', async () => {
  const p = await pagina();
  const alvo = DADOS.pessoas.find(x => (x.conhecer || []).length);
  await p.evaluate(id => window.RNQ_APP.select(id, true), alvo.id);
  const card = p.locator('#card');
  await card.waitFor({ state: 'visible' });
  const t = await card.textContent();
  for (const s of ['Comunidades', 'Temas', 'Atuação', 'Pode ser bom conhecer', 'Eu conheço essa pessoa', 'Atualizar meu perfil'])
    assert.ok(t.includes(s), `faltou "${s}" no card`);
  await p.waitForTimeout(1200); await p.screenshot({ path: path.join(FOTOS, '02-card.png') });
  await card.locator('[data-pessoa]').first().click();
  assert.notEqual(await p.evaluate(() => window.RNQ_APP.selId), alvo.id, 'clicar em "Pode ser bom conhecer" deveria abrir outra pessoa');
  await p.close();
});

await teste('perfil: exige ao menos uma resposta e mostra aviso de prévia local', async () => {
  const p = await pagina();
  await p.evaluate(id => window.RNQ_APP.select(id), DADOS.pessoas[0].id);
  await p.click('#card [data-acao="perfil"]');
  await p.click('#fx button[type=submit]');
  assert.match(await p.textContent('#fxMsg'), /pelo menos uma/);
  await p.fill('#fx textarea[name=compartilha]', 'Facilitação de rodas de conversa');
  await p.click('#fx button[type=submit]');
  assert.match(await p.textContent('#fxMsg'), /Prévia local/);
  await p.close();
});

await teste('mural vazio mostra convite e passos', async () => {
  const p = await pagina({ hash: '#mural' });
  await p.locator('#vMural').waitFor({ state: 'visible' });
  if (!DADOS.mural.length) assert.match(await p.textContent('#muralGrid'), /primeira oferta/);
  await p.screenshot({ path: path.join(FOTOS, '03-mural-vazio.png') });
  await p.close();
});

await teste('mural (demo): filtros, "quem trabalha com isso" e resposta', async () => {
  const p = await pagina({ query: '?demo=1', hash: '#mural' });
  await p.locator('#vMural').waitFor({ state: 'visible' });
  assert.ok(await p.locator('#demoBanner').isVisible());
  const abertos = DADOS.mural.filter(m => m.status === 'aberto').length + 3;
  assert.equal(await p.locator('#muralGrid .item').count(), abertos);
  await p.click('#segMural button[data-f="pedido"]');
  assert.equal(await p.locator('#muralGrid .item .tag.pedido').count(), await p.locator('#muralGrid .item').count());
  assert.ok(await p.locator('#muralGrid .match').count() >= 1, 'pedido deveria sugerir quem trabalha com o tema');
  await p.click('#segMural button[data-f=""]');
  await p.check('#fMuralAtendidos');
  assert.equal(await p.locator('#muralGrid .item.fechado').count(), DADOS.mural.filter(m => m.status === 'atendido').length + 1);
  await p.uncheck('#fMuralAtendidos');
  await p.screenshot({ path: path.join(FOTOS, '04-mural-demo.png') });
  await p.click('#muralGrid [data-responder]');
  await p.click('#fx button[type=submit]');
  assert.match(await p.textContent('#fxMsg'), /Preencha/);
  await p.fill('#fx input[name=nome]', 'Teste'); await p.fill('#fx input[name=contato]', 'teste@exemplo.org');
  await p.click('#fx button[type=submit]');
  assert.match(await p.textContent('#fxMsg'), /Prévia local/);
  await p.close();
});

await teste('publicar no mural: exige concordância e limita a 3 áreas', async () => {
  const p = await pagina({ hash: '#mural' });
  await p.click('#btnPublicar');
  await p.fill('#fx input[name=titulo]', 'Ofereço mentoria'); await p.fill('#fx input[name=nome]', 'Teste');
  await p.fill('#fx input[name=contato]', '11 99999-0000');
  const caixas = p.locator('#fx .areas input');
  for (let i = 0; i < 3; i++) await caixas.nth(i).check();
  assert.ok(await caixas.nth(3).isDisabled(), '4ª área deveria ficar bloqueada');
  await p.click('#fx button[type=submit]');
  assert.match(await p.textContent('#fxMsg'), /concordância/);
  await p.check('#fx input[name=consentimento]');
  await p.screenshot({ path: path.join(FOTOS, '05-publicar.png') });
  await p.click('#fx button[type=submit]');
  assert.match(await p.textContent('#fxMsg'), /Prévia local/);
  await p.close();
});

await teste('iniciativas (demo) e proposta', async () => {
  const p = await pagina({ query: '?demo=1', hash: '#iniciativas' });
  await p.locator('#vIni').waitFor({ state: 'visible' });
  assert.equal(await p.locator('#iniGrid .item').count(), DADOS.iniciativas.filter(i => i.status === 'ativa').length + 2);
  await p.click('#segIni button[data-f="Projeto"]');
  assert.ok(await p.locator('#iniGrid .item').count() >= 1);
  await p.screenshot({ path: path.join(FOTOS, '06-iniciativas.png') });
  await p.click('#btnPropor');
  assert.ok(await p.locator('#fx select[name=tipo]').isVisible());
  await p.close();
});

await teste('organizações e 3D (pessoas e organizações)', async () => {
  const p = await pagina();
  await p.click('.main-tabs button[data-v="orgs"]');
  await p.waitForTimeout(1500);
  assert.ok(await p.locator('#vOrgs svg path').count() > 10);
  await p.click('.main-tabs button[data-v="3d"]');
  await p.waitForFunction(() => document.querySelector('#view3d canvas'), null, { timeout: 15000 });
  await p.click('#t3d button[data-m="orgs"]');
  await p.waitForTimeout(3000);
  await p.screenshot({ path: path.join(FOTOS, '07-3d-orgs.png') });
  assert.deepEqual(p.erros, []);
  await p.close();
});

await teste('sair do mapa pelo rodapé esconde a pessoa na sessão', async () => {
  const p = await pagina();
  const antes = await p.locator('#vPessoas svg path').count();
  await p.click('#lnkSair');
  await p.selectOption('#oSel', DADOS.pessoas[1].id);
  await p.click('#oCont'); await p.click('#oSim');
  await p.waitForTimeout(600);
  assert.equal(await p.locator('#vPessoas svg path').count() < antes, true);
  assert.match(await p.textContent('#dlgBody'), /Pedido registrado/);
  await p.close();
});

await teste('Como participar abre o guia', async () => {
  const p = await pagina();
  await p.click('#btnParticipar');
  assert.match(await p.textContent('#dlgBody'), /Encontre-se no mapa/);
  await p.screenshot({ path: path.join(FOTOS, '08-como-participar.png') });
  await p.close();
});

await teste('link direto para pessoa (#p/id) abre o card', async () => {
  const p = await pagina({ hash: '#p/' + DADOS.pessoas[2].id });
  await p.locator('#card.show').waitFor({ timeout: 5000 });
  assert.match(await p.textContent('#cBody'), new RegExp(DADOS.pessoas[2].nome.split(' ')[0]));
  await p.close();
});

await teste('celular: sem rolagem horizontal no mapa e no mural', async () => {
  for (const hash of ['', '#mural']) {
    const p = await pagina({ w: 390, h: 820, hash, query: '?demo=1' });
    await p.waitForTimeout(1500);
    const [sw, iw] = await p.evaluate(() => [document.documentElement.scrollWidth, innerWidth]);
    assert.ok(sw <= iw + 1, `rolagem horizontal em ${hash || 'pessoas'}: ${sw} > ${iw}`);
    await p.screenshot({ path: path.join(FOTOS, `09-celular${hash ? '-mural' : ''}.png`) });
    await p.close();
  }
});

await teste('noindex e formulários Netlify declarados', async () => {
  const html = fs.readFileSync(SITE, 'utf8');
  assert.match(html, /<meta name="robots" content="noindex, nofollow">/);
  for (const f of ['sugestao-ligacao', 'opt-out', 'opt-in', 'perfil', 'mural', 'mural-resposta', 'iniciativa', 'iniciativa-participar'])
    assert.match(html, new RegExp(`<form name="${f}" data-netlify="true"`), `formulário ${f} não declarado`);
});

await teste('busca por trecho do nome (Enter) abre o card', async () => {
  const p = await pagina();
  const alvo = DADOS.pessoas[3];
  await p.fill('#q', alvo.nome.split(' ')[0].slice(0, 4).toLowerCase());
  await p.press('#q', 'Enter');
  await p.locator('#card.show').waitFor({ timeout: 4000 });
  await p.keyboard.press('Escape');
  assert.equal(await p.locator('#card.show').count(), 0, 'Esc deveria fechar o card');
  await p.close();
});

await teste('link direto para item do mural (#m/id) e botão "Copiar link"', async () => {
  const p = await pagina({ query: '?demo=1', hash: '#m/demo-3' });
  await p.locator('#item-demo-3').waitFor({ timeout: 5000 });
  assert.equal(await p.evaluate(() => window.RNQ_APP.view), 'mural');
  assert.ok(await p.locator('#item-demo-3 [data-link="m/demo-3"]').count() === 1);
  const p2 = await pagina({ query: '?demo=1', hash: '#m/demo-4' });     // item atendido: abre com "mostrar atendidos"
  await p2.locator('#item-demo-4').waitFor({ timeout: 5000 });
  assert.ok(await p2.isChecked('#fMuralAtendidos'));
  await p.close(); await p2.close();
});

await teste('chips claros têm texto escuro (contraste)', async () => {
  const p = await pagina();
  await p.evaluate(id => window.RNQ_APP.select(id), DADOS.pessoas.find(x => x.comunidades.length).id);
  const cores = await p.$$eval('#card .chip:not(.outline)', els => els.map(e => [getComputedStyle(e).backgroundColor, getComputedStyle(e).color]));
  for (const [bg, fg] of cores) {
    const lum = s => { const [r, g, b] = s.match(/\d+/g).map(Number); return 0.299 * r + 0.587 * g + 0.114 * b; };
    assert.ok(Math.abs(lum(bg) - lum(fg)) > 90, `contraste baixo: ${bg} / ${fg}`);
  }
  await p.close();
});

await teste('sem chamadas a CDNs (bibliotecas servidas pelo site)', async () => {
  const p = await pagina();
  const externos = [];
  p.on('request', r => { const u = r.url(); if (u.startsWith('http') && !u.includes('fonts.g')) externos.push(u); });
  await p.click('.main-tabs button[data-v="3d"]');
  await p.waitForFunction(() => document.querySelector('#view3d canvas'), null, { timeout: 15000 });
  assert.deepEqual(externos, []);
  await p.close();
});

// ---------------------------------------------------------------- idiomas (PT | EN)
await teste('?lang=en abre em inglês (interface e nomes dos grupos)', async () => {
  const p = await pagina({ query: '?lang=en' });
  assert.equal(await p.textContent('.brand h1'), 'Novo Quilombo Network');
  assert.equal(await p.getAttribute('html', 'lang'), 'en');
  assert.equal(await p.textContent('.main-tabs button[data-v="pessoas"]'), 'People');
  assert.equal(await p.textContent('#dimtitle'), 'Communities');
  assert.match(await p.textContent('#coms'), /Technology/);
  assert.match(await p.textContent('#stats'), /people/);
  assert.equal(await p.getAttribute('#q', 'placeholder'), 'Search for a person or organization…');
  assert.ok(await p.locator('.lang button[data-lang="en"].on').count() === 1);
  await p.waitForTimeout(2500);
  assert.match(await p.locator('#vPessoas svg').textContent(), /Technology/);
  assert.deepEqual(p.erros, []);
  await p.screenshot({ path: path.join(FOTOS, '10-en-pessoas.png') });
  await p.close();
});

await teste('navegador em inglês abre em inglês; em português, em português', async () => {
  const en = await pagina({ locale: 'en-US' });
  assert.equal(await en.textContent('#btnParticipar'), 'How to take part');
  const pt = await pagina({ locale: 'pt-BR' });
  assert.equal(await pt.textContent('#btnParticipar'), 'Como participar');
  await en.close(); await pt.close();
});

await teste('botão PT | EN troca tudo sem recarregar e mantém o card aberto', async () => {
  const p = await pagina();
  const alvo = DADOS.pessoas.find(x => (x.conhecer || []).length && x.comunidades.length);
  await p.evaluate(id => window.RNQ_APP.select(id, true), alvo.id);
  await p.locator('#card.show').waitFor();
  assert.match(await p.textContent('#card'), /Pode ser bom conhecer/);
  await p.click('.lang button[data-lang="en"]');
  assert.equal(await p.evaluate(() => window.RNQ_APP.selId), alvo.id);
  const card = await p.textContent('#card');
  for (const s of ['Communities', 'Might be good to meet', 'I know this person', 'Update my profile'])
    assert.ok(card.includes(s), `faltou "${s}" no card em inglês`);
  assert.ok(p.url().includes('#p/' + alvo.id), 'o link da pessoa deveria continuar no endereço');
  await p.waitForTimeout(800); await p.screenshot({ path: path.join(FOTOS, '11-en-card.png') });
  await p.click('.lang button[data-lang="pt"]');
  assert.match(await p.textContent('#card'), /Eu conheço essa pessoa/);
  assert.equal(await p.textContent('#dimtitle'), 'Comunidades');
  assert.deepEqual(p.erros, []);
  await p.close();
});

await teste('escolha de idioma continua depois de recarregar', async () => {
  const ctx = await browser.newContext({ locale: 'pt-BR' });
  const p = await ctx.newPage();
  await p.route('**fonts.g*/**', r => r.abort());
  await p.goto('file://' + SITE);
  await p.waitForFunction(() => window.RNQ_APP);
  await p.click('.lang button[data-lang="en"]');
  await p.reload(); await p.waitForFunction(() => window.RNQ_APP);
  assert.equal(await p.textContent('.brand h1'), 'Novo Quilombo Network');
  await ctx.close();
});

await teste('formulários em inglês mantêm os mesmos campos do Netlify', async () => {
  const p = await pagina({ query: '?lang=en', hash: '#mural' });
  await p.click('#btnPublicar');
  assert.match(await p.textContent('#dlgBody'), /Post on the board/);
  const nomes = await p.$$eval('#fx [name]', els => [...new Set(els.map(e => e.name))].sort());
  assert.deepEqual(nomes, ['areas', 'bot', 'consentimento', 'contato', 'descricao', 'no_mapa', 'nome', 'tipo', 'titulo']);
  assert.deepEqual(await p.$$eval('#fx input[name=tipo]', els => els.map(e => e.value)), ['Oferta', 'Pedido']);
  const area = DADOS.temas.find(x => x.nome_en && x.nome_en !== x.nome);
  const caixa = p.locator(`#fx .areas input[value="${area.nome}"]`);
  assert.equal(await caixa.count(), 1, 'valor da área continua em português');
  assert.match(await caixa.locator('xpath=..').textContent(), new RegExp(area.nome_en.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  await p.click('#fx button[type=submit]');
  assert.match(await p.textContent('#fxMsg'), /Please fill in/);
  await p.close();
  const q = await pagina({ query: '?lang=en', hash: '#iniciativas' });
  await q.click('#btnPropor');
  assert.deepEqual(await q.$$eval('#fx select[name=tipo] option', os => os.map(o => o.value)), ['Projeto', 'Encontro', 'Grupo de prática']);
  assert.deepEqual(await q.$$eval('#fx select[name=tipo] option', os => os.map(o => o.textContent)), ['Project', 'Gathering', 'Practice group']);
  await q.close();
});

await teste('mural (demo) em inglês: etiquetas, áreas e datas traduzidas; texto das pessoas no original', async () => {
  const p = await pagina({ query: '?demo=1&lang=en', hash: '#mural' });
  await p.locator('#vMural').waitFor({ state: 'visible' });
  const t = await p.textContent('#muralGrid');
  assert.match(t, /Request/); assert.match(t, /I can help/); assert.match(t, /days ago/);
  assert.match(t, /Facilitation & collective processes/);
  assert.match(t, /Procuro facilitação/, 'o texto publicado pela pessoa não é traduzido');
  assert.match(await p.textContent('#fMuralArea'), /All areas/);
  await p.selectOption('#fMuralArea', 'ESG');
  assert.ok(await p.locator('#muralGrid .item').count() >= 1, 'filtro por área continua funcionando em inglês');
  await p.screenshot({ path: path.join(FOTOS, '12-en-mural-demo.png') });
  await p.close();
});

await teste('celular em inglês: sem rolagem horizontal', async () => {
  const p = await pagina({ w: 390, h: 820, query: '?lang=en' });
  await p.waitForTimeout(1200);
  const [sw, iw] = await p.evaluate(() => [document.documentElement.scrollWidth, innerWidth]);
  assert.ok(sw <= iw + 1, `rolagem horizontal: ${sw} > ${iw}`);
  await p.screenshot({ path: path.join(FOTOS, '13-en-celular.png') });
  await p.close();
});

await teste('"Sobre os dados" no rodapé e pelo link #sobre (PT e EN)', async () => {
  const p = await pagina();
  await p.click('#lnkSobre');
  const t = await p.textContent('#dlgBody');
  assert.match(t, /LGPD/); assert.match(t, /Quero sair do mapa/); assert.match(t, /Responsável/);
  if (DADOS.sobre && DADOS.sobre.contato) assert.ok(await p.locator(`#dlgBody a[href="mailto:${DADOS.sobre.contato}"]`).count() === 1);
  await p.screenshot({ path: path.join(FOTOS, '14-sobre.png') });
  await p.close();
  const en = await pagina({ query: '?lang=en', hash: '#sobre' });
  await en.locator('#dlgBody').waitFor({ state: 'visible' });
  assert.match(await en.textContent('#dlgBody'), /About the data/);
  assert.deepEqual(en.erros, []);
  await en.close();
});

await browser.close();
console.log(`\n${ok} ok, ${falhas} falha(s)`);
process.exit(falhas ? 1 : 0);
