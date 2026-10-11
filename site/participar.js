'use strict';
/* "Faça parte" (participar.html): cadastro em 5 passos com prévia do card.
   - Envia para o formulário "participar" do Netlify (declarado escondido no index.html).
   - As escolhas são enviadas SEMPRE em português, nos dois idiomas, para cair iguais na planilha de tecelagem.
   - Temas, comunidades, atuação e fios vêm de data.js (RNQ_DATA.listas, gerado pelo exportar.py a partir de
     rnq/config.py); os textos da página estão em i18n.js (chaves pa_*). */
(function () {
  const I = window.I18N, t = I.t;
  const D = window.RNQ_DATA || {};
  const L = D.listas || { temas: [], comunidades: [], atuacoes: [], fios: [] };
  const LOCAL = location.protocol === 'file:';
  const DEMO = new URLSearchParams(location.search).has('demo');
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const MAX_TEMAS = 7, MAX_FIOS = 4, PASSOS = 5;
  const OUTRO = 'Outro', OUTRA = 'Outra';
  // valores sempre em PT (vão para a planilha); o texto na tela vem de i18n.js ("op:<valor>")
  const OFERTAS = ['Facilitar um círculo de conversa', 'Mentoria', 'Facilitar um encontro de cocriação', 'Conduzir uma meditação', OUTRA];
  const FORMATOS = ['Café 1:1 on-line', 'Encontro em grupo', 'Mentoria', 'Projeto conjunto', 'Encontro presencial'];
  const NECESSIDADES = ['Economia local & trabalho digno', 'Alimento & água', 'Natureza & território', 'Energia', 'Moradia',
    'Paz & segurança comunitária', 'Ajuda mútua entre vizinhos', 'Inclusão de quem está à margem', 'Saúde & cuidado',
    'Educação & mentoria', 'Arte & cultura', 'Espiritualidade a serviço'];
  const TIPOS_ORG = ['Empresa', 'ONG ou coletivo', 'Negócio de impacto', 'Academia ou pesquisa', 'Setor público', 'Rede ou comunidade'];
  const OBJETIVOS = ['acompanhar', 'conversar', 'fazer', 'tecer'];

  const nomeDe = {};                       // valor PT -> objeto da lista (para o nome em inglês)
  [...L.temas, ...L.comunidades, ...L.atuacoes].forEach(g => { nomeDe[g.nome] = g; });
  const fioPorNome = Object.fromEntries(L.fios.map(f => [f.nome, f]));
  const rot = v => v === OUTRO ? t('pa_outro') : v === OUTRA ? t('pa_outra')
    : nomeDe[v] ? I.nome(nomeDe[v]) : (t('op:' + v) === 'op:' + v ? v : t('op:' + v));

  const S = { quem: 'pessoa', temas: [], atuacao: [], comunidades: [], ofertas: [], formatos: [], fios: [] };
  let passo = 0, enviado = false;
  const radio = n => (document.querySelector(`input[name=${n}]:checked`) || {}).value;

  // ------------------------------------------------------------ chips
  const LISTAS = {
    temas: () => L.temas.map(g => g.nome).concat(OUTRO),
    atuacao: () => L.atuacoes.map(g => g.nome),
    comunidades: () => L.comunidades.map(g => g.nome).concat(OUTRA),
    ofertas: () => OFERTAS, formatos: () => FORMATOS
  };
  const LIMITE = { temas: MAX_TEMAS };
  function desenharChips(k) {
    const box = $(k), max = LIMITE[k] || 0, a = S[k];
    box.innerHTML = LISTAS[k]().map(v => `<button type="button" class="chip" data-v="${esc(v)}" aria-pressed="${a.includes(v)}">${esc(rot(v))}</button>`).join('');
    sincronizarChips(k);
  }
  function sincronizarChips(k) {
    const a = S[k], max = LIMITE[k] || 0;
    [...$(k).children].forEach(b => { const on = a.includes(b.dataset.v); b.setAttribute('aria-pressed', on); b.disabled = !!max && !on && a.length >= max; });
    if (k === 'temas') $('c-temas').textContent = t('pa_de', { n: a.length, max: MAX_TEMAS });
    if (k === 'temas') $('outroTema').hidden = !a.includes(OUTRO);
    if (k === 'comunidades') $('outraCom').hidden = !a.includes(OUTRA);
  }
  Object.keys(LISTAS).forEach(k => $(k).addEventListener('click', e => {
    const b = e.target.closest('.chip'); if (!b || b.disabled) return;
    const a = S[k], v = b.dataset.v, i = a.indexOf(v);
    i >= 0 ? a.splice(i, 1) : a.push(v);
    sincronizarChips(k); render();
  }));

  function desenharFios() {
    $('fios').innerHTML = L.fios.map(f => `<button type="button" class="fio" data-n="${esc(f.nome)}" aria-pressed="false"><b>${esc(I.nome(f))}</b><i>${esc(I.lang === 'en' && f.pergunta_en ? f.pergunta_en : f.pergunta)}</i></button>`).join('');
    sincronizarFios();
  }
  function sincronizarFios() {
    [...$('fios').children].forEach(b => { const on = S.fios.includes(b.dataset.n); b.setAttribute('aria-pressed', on); b.disabled = !on && S.fios.length >= MAX_FIOS; });
    $('c-fios').textContent = t('pa_de', { n: S.fios.length, max: MAX_FIOS });
  }
  $('fios').addEventListener('click', e => {
    const b = e.target.closest('.fio'); if (!b || b.disabled) return;
    const i = S.fios.indexOf(b.dataset.n); i >= 0 ? S.fios.splice(i, 1) : S.fios.push(b.dataset.n);
    sincronizarFios(); render();
  });

  function desenharObjetivos() {
    const atual = radio('abertura');
    $('abertura').innerHTML = OBJETIVOS.map(o => `<label class="rc"><input type="radio" name="abertura" value="${o}" ${o === atual ? 'checked' : ''}><div><b>${t('pa_obj_' + o)}</b><span>${t('pa_obj_' + o + '_d')}</span></div></label>`).join('');
  }
  function opcoes(sel, lista, vazio, rotulo = rot) {
    const atual = sel.value;
    sel.innerHTML = `<option value="">${esc(vazio)}</option>` + lista.map(v => `<option value="${esc(v)}">${esc(rotulo(v))}</option>`).join('');
    sel.value = atual;
  }
  function desenharSelects() {
    opcoes($('orgtipo'), TIPOS_ORG, t('pa_escolha'));
    opcoes($('necessidade'), NECESSIDADES, t('pa_escolha_uma'));
    opcoes($('bdia'), Array.from({ length: 31 }, (_, i) => String(i + 1)), t('pa_dia'), v => v);
    const meses = Array.from({ length: 12 }, (_, i) => new Date(2026, i, 1).toLocaleDateString(I.locale(), { month: 'short' }).replace('.', ''));
    opcoes($('bmes'), Array.from({ length: 12 }, (_, i) => String(i + 1)), t('pa_mes'), v => meses[+v - 1]);
  }

  // ------------------------------------------------------------ quem responde
  function setQuem(q) {
    S.quem = q;
    $('whoP').setAttribute('aria-pressed', q === 'pessoa'); $('whoO').setAttribute('aria-pressed', q === 'organizacao');
    $('orgbox').hidden = q !== 'organizacao';
    $('whoHelp').textContent = t(q === 'organizacao' ? 'pa_quem_org_help' : 'pa_quem_pessoa_help');
    $('orgLabel').innerHTML = esc(t('pa_org')) + (q === 'organizacao' ? ' <span class="req">*</span>' : ` <small>${esc(t('pa_opcional'))}</small>`);
    render();
  }
  $('whoP').onclick = () => setQuem('pessoa');
  $('whoO').onclick = () => setQuem('organizacao');

  // ------------------------------------------------------------ passos
  function desenharPassos() {
    const nomes = [1, 2, 3, 4, 5].map(i => t('pa_passo' + i));
    $('steps').innerHTML = nomes.map((s, i) => `<li class="${i < passo ? 'done' : i === passo ? 'cur' : ''}"><button type="button" data-i="${i}" ${i > passo ? 'disabled' : ''} aria-current="${i === passo ? 'step' : 'false'}"><span class="bar"></span><span class="lbl">${esc(s)}</span></button></li>`).join('');
    document.querySelectorAll('[data-passo]').forEach(p => { p.textContent = t('pa_passo_de', { n: +p.dataset.passo, total: PASSOS }); });
  }
  $('steps').addEventListener('click', e => { const b = e.target.closest('button'); if (b && !b.disabled) ir(+b.dataset.i); });
  function ir(i) {
    passo = i;
    document.querySelectorAll('fieldset').forEach(f => { f.hidden = +f.dataset.step !== passo; });
    $('prev').style.visibility = passo ? 'visible' : 'hidden';
    $('next').textContent = passo === PASSOS - 1 ? t('pa_entrar') : t('continuar');
    desenharPassos();
    const intro = $('intro');
    if (passo > 0 && intro.getBoundingClientRect().top < 0) $('steps').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion:reduce)').matches ? 'auto' : 'smooth' });
  }
  function checar() {
    const erros = [];
    const mostrar = (id, ruim) => { $(id).hidden = !ruim; if (ruim) erros.push(id); };
    if (passo === 0) {
      mostrar('e-nome', !$('nome').value.trim());
      mostrar('e-contato', !$('contato').value.trim());
      mostrar('e-org', S.quem === 'organizacao' && !$('org').value.trim());
    }
    if (passo === 1) mostrar('e-temas', !temasEscolhidos().length);
    if (passo === 3) mostrar('e-abertura', !radio('abertura'));
    if (passo === 4) { mostrar('e-vis', !radio('vis')); mostrar('e-maior', !$('maior').checked); }
    if (erros.length) { const el = $(erros[0]); el.scrollIntoView({ block: 'center', behavior: 'smooth' }); }
    return !erros.length;
  }
  $('form').addEventListener('submit', e => { e.preventDefault(); if (enviado || !checar()) return; if (passo < PASSOS - 1) ir(passo + 1); else enviar(); });
  $('prev').onclick = () => ir(Math.max(0, passo - 1));
  $('form').addEventListener('input', render);
  $('form').addEventListener('change', render);

  // ------------------------------------------------------------ dados
  const temasEscolhidos = () => S.temas.filter(x => x !== OUTRO).concat(S.temas.includes(OUTRO) && $('outroTema').value.trim() ? [$('outroTema').value.trim()] : []);
  const comunidadesEscolhidas = () => S.comunidades.filter(x => x !== OUTRA).concat(S.comunidades.includes(OUTRA) && $('outraCom').value.trim() ? [$('outraCom').value.trim()] : []);
  const teceFios = () => ['fazer', 'tecer'].includes(radio('abertura'));
  const junta = a => a.join('; ');

  // Campos enviados ao Netlify. Os nomes batem com rnq/tecelagem.py (FORMULARIOS['participar']) — há teste para isso.
  function campos() {
    const dia = $('bdia').value, mes = $('bmes').value;
    return {
      quem: S.quem === 'organizacao' ? 'organização' : 'pessoa',
      nome: $('nome').value.trim(), contato: $('contato').value.trim(), linkedin: $('linkedin').value.trim(),
      cargo: $('cargo').value.trim(), organizacao: $('org').value.trim(),
      org_site: S.quem === 'organizacao' ? $('orgsite').value.trim() : '',
      org_tipo: S.quem === 'organizacao' ? $('orgtipo').value : '',
      proposito: $('proposito').value.trim(), local: $('local').value.trim(),
      aniversario: dia && mes ? `${dia.padStart(2, '0')}/${mes.padStart(2, '0')}` : '',
      temas: junta(S.temas.filter(x => x !== OUTRO)),
      tema_outro: S.temas.includes(OUTRO) ? $('outroTema').value.trim() : '',
      atuacao: junta(S.atuacao),
      comunidades: junta(S.comunidades.filter(x => x !== OUTRA)),
      comunidade_outra: S.comunidades.includes(OUTRA) ? $('outraCom').value.trim() : '',
      quer_orgs: $('querOrgs').value.trim(), necessidade: $('necessidade').value,
      ofertas: junta(S.ofertas.filter(x => x !== OUTRA)), oferta: $('oferta').value.trim(), pedido: $('pedido').value.trim(),
      mural: $('mural').checked ? 'sim' : 'não',
      objetivo: radio('abertura') || '', fios: teceFios() ? junta(S.fios) : '', formatos: junta(S.formatos),
      indicacoes: ['ind1', 'ind2', 'ind3'].map(id => $(id).value.trim()).filter(Boolean).join(' | '),
      visibilidade: radio('vis') || '', maior_18: $('maior').checked ? 'sim' : 'não',
      idioma: I.lang, origem: (new URLSearchParams(location.search).get('origem') || '').slice(0, 40),
      bot: $('bot').value
    };
  }

  async function enviar() {
    const msg = $('envioMsg'), botao = $('next');
    msg.innerHTML = '';
    let r = 'local';
    if (!LOCAL && !DEMO) {
      botao.disabled = true;
      try {
        const resp = await fetch('/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({ 'form-name': 'participar', ...campos() }).toString() });
        r = resp.ok ? 'ok' : 'erro';
      } catch (e) { r = 'erro'; }
      botao.disabled = false;
    }
    if (r === 'erro') { msg.innerHTML = `<p class="aviso erro">${esc(t('res_erro'))}</p>`; return; }
    enviado = true;
    concluir(r === 'local');
  }

  function concluir(previa) {
    $('form').hidden = true; $('steps').hidden = true; $('intro').hidden = true; $('done').hidden = false;
    textosConcluido();
    $('doneLocal').innerHTML = previa ? `<p class="aviso">${esc(t('res_local'))}</p>` : '';
    window.scrollTo(0, 0);
  }
  function textosConcluido() {
    const primeiro = $('nome').value.trim().split(/\s+/)[0] || '';
    $('doneTitle').textContent = t('pa_done_t', primeiro);
    const ob = radio('abertura'), extra = ob ? t('pa_done_' + ob) : '';
    $('doneText').textContent = (radio('vis') === 'fora' ? t('pa_done_fora') : t('pa_done_mapa')) + (extra ? ' ' + extra : '');
  }

  // ------------------------------------------------------------ prévia do card
  function limparErros() {
    const ok = { 'e-nome': () => $('nome').value.trim(), 'e-contato': () => $('contato').value.trim(),
      'e-org': () => S.quem !== 'organizacao' || $('org').value.trim(), 'e-temas': () => temasEscolhidos().length,
      'e-abertura': () => radio('abertura'), 'e-vis': () => radio('vis'), 'e-maior': () => $('maior').checked };
    for (const id in ok) if (!$(id).hidden && ok[id]()) $(id).hidden = true;
  }
  function render() {
    limparErros();
    const nome = $('nome').value.trim(), cargo = $('cargo').value.trim(), org = $('org').value.trim();
    const ini = (nome || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]).join('').toUpperCase() || '?';
    const sub = [cargo, org].filter(Boolean).join(' · ');
    const vis = radio('vis');
    $('fiosBox').hidden = !teceFios();
    $('c-prop').textContent = $('proposito').value.length + '/432';
    const sec = (titulo, corpo) => `<div class="sec"><h5>${titulo}</h5>${corpo}</div>`;
    const tags = (a, c) => a.length ? `<div class="pc">${a.map(x => `<span class="${c || ''}">${esc(x)}</span>`).join('')}</div>` : `<p class="empty">${esc(t('pa_nao_escolhido'))}</p>`;
    const of = $('oferta').value.trim(), pe = $('pedido').value.trim(), prop = $('proposito').value.trim();
    const ofs = S.ofertas.filter(o => o !== OUTRA).map(rot);
    const temas = temasEscolhidos().map(v => S.temas.includes(v) ? rot(v) : v);
    const coms = comunidadesEscolhidas().map(v => S.comunidades.includes(v) ? rot(v) : v);
    const fios = S.fios.map(n => fioPorNome[n] ? I.nome(fioPorNome[n]) : n);
    $('card').className = 'card' + (vis === 'fora' ? ' private' : '');
    $('card').innerHTML = `<div class="top"><div class="av" aria-hidden="true">${esc(ini)}</div><div style="min-width:0"><h4>${nome ? esc(nome) : `<span class="empty">${esc(t('pa_seu_nome'))}</span>`}</h4><div class="sub">${esc(sub) || esc(t('pa_cargo_org'))}</div></div></div>
      ${prop ? `<p class="prop">${esc(prop)}</p>` : ''}
      ${sec(esc(t('dim_temas')), tags(temas, 't'))}
      ${sec(esc(t('dim_comunidades')), tags(coms))}
      ${teceFios() && fios.length ? sec(esc(t('fios_tece')), tags(fios, 't')) : ''}
      ${sec(`<span style="color:var(--oferta)">${esc(t('pode_oferecer'))}</span>`, (ofs.length || of) ? `${ofs.length ? tags(ofs) : ''}${of ? `<p style="margin-top:${ofs.length ? 6 : 0}px">${esc(of)}</p>` : ''}` : `<p class="empty">${esc(t('pa_oferta_aqui'))}</p>`)}
      ${sec(`<span style="color:var(--pedido)">${esc(t('procura'))}</span>`, pe ? `<p>${esc(pe)}</p>` : `<p class="empty">${esc(t('pa_pedido_aqui'))}</p>`)}
      <div class="vis"><span class="dot"></span>${esc(vis === 'fora' ? t('pa_vis_fora_card') : vis === 'mapa' ? t('pa_vis_mapa_card') : t('pa_vis_escolha'))}</div>`;
  }

  // ------------------------------------------------------------ privacidade, convite, idioma
  function privacidade() {
    const c = D.sobre && D.sobre.contato;
    $('privacidade').innerHTML = esc(t('pa_privacidade')) + (c ? ` <a href="mailto:${esc(c)}">${esc(c)}</a>.` : '');
  }
  const linkConvite = () => (LOCAL ? 'https://mapa-novoquilombo.netlify.app' : location.origin) + '/participar?origem=convite';
  $('copyBtn').onclick = async () => {
    const v = $('share').value;
    try { await navigator.clipboard.writeText(v); $('copied').textContent = t('link_copiado'); }
    catch (e) { $('share').select(); $('copied').textContent = t('pa_selecione_copie'); }
  };

  function tudo() {
    I.aplicar();
    document.title = t('pa_titulo_aba');
    ['temas', 'atuacao', 'comunidades', 'ofertas', 'formatos'].forEach(desenharChips);
    desenharFios(); desenharObjetivos(); desenharSelects(); setQuem(S.quem); ir(passo); privacidade();
    if (enviado) textosConcluido();
    render();
  }
  document.querySelectorAll('[data-lang]').forEach(b => { b.onclick = () => I.definir(b.dataset.lang); });
  I.aoMudar(tudo);
  $('share').value = linkConvite();
  const params = new URLSearchParams(location.search).get('lang');
  if (params) $('voltar').href = './?lang=' + I.lang;

  // modo demonstração (?demo=1): exemplo pronto e nada é enviado
  if (DEMO) {
    $('demoBanner').hidden = false; $('exemplo').hidden = false;
    $('exemplo').onclick = () => {
      setQuem('pessoa');
      Object.assign($('nome'), { value: 'Marina Exemplo' }); $('contato').value = 'marina@exemplo.org';
      $('cargo').value = 'Facilitadora'; $('org').value = 'Coletivo Raiz (fictício)'; $('local').value = 'Salvador, BA';
      $('bdia').value = '14'; $('bmes').value = '3';
      $('proposito').value = 'Criar espaços onde jovens descubram sua potência e se reconectem com a própria ancestralidade.';
      S.temas = L.temas.slice(0, 3).map(g => g.nome); S.atuacao = L.atuacoes.slice(3, 4).map(g => g.nome);
      S.comunidades = L.comunidades.slice(0, 2).map(g => g.nome); S.ofertas = [OFERTAS[0], OFERTAS[3]];
      ['temas', 'atuacao', 'comunidades', 'ofertas'].forEach(sincronizarChips);
      $('necessidade').value = NECESSIDADES[9]; $('querOrgs').value = 'Instituto Fonte; uma escola Waldorf em Salvador';
      $('oferta').value = 'Círculo de 2h, on-line, para coletivos que estão começando.';
      $('pedido').value = 'Conhecer quem trabalha com educação ambiental em escolas públicas do Nordeste.';
      document.querySelector('input[name=abertura][value=tecer]').checked = true;
      S.fios = L.fios.filter(f => ['conexao', 'acolhida', 'roda'].includes(f.id)).map(f => f.nome); sincronizarFios();
      render();
    };
  }

  tudo();
  window.RNQ_PARTICIPAR = { campos, ir, get passo() { return passo; }, estado: S };
})();
