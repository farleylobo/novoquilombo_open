'use strict';
/* Rede Novo Quilombo — visão pública.
   Dados: data.js (window.RNQ_DATA), gerado por exportar.py. Nada aqui é escrito no servidor:
   todo envio vai para o Netlify Forms e só aparece no site depois da moderação. */

const D = window.RNQ_DATA;
const { t, quando } = window.I18N;
const nomeDe = window.I18N.nome;
D.mural = D.mural || []; D.iniciativas = D.iniciativas || []; D.papeis = D.papeis || [];
D.temas = D.temas || []; D.atuacoes = D.atuacoes || [];
const DEMO = new URLSearchParams(location.search).has('demo') && window.RNQ_DEMO;
if (DEMO) { D.mural = D.mural.concat(DEMO.mural); D.iniciativas = D.iniciativas.concat(DEMO.iniciativas); }
const LOCAL = location.protocol === 'file:';
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const slug = s => String(s || '').normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

// ---------------------------------------------------------------- modelo
const PAL = ['#E07A4A', '#3FA58A', '#E3B341', '#A77BCA', '#4F8FD6', '#C9774F', '#7DB34A', '#D6607F', '#4FB3BD', '#B8A04A', '#8E6FD8', '#2E8B57', '#D98E04', '#5B7DB1', '#C0504D', '#6AA84F', '#B65FCF', '#3D9970'];
const NEUTRAL = '#9C8B7A', SEM = '__sem';
const dimDe = (k, lista, campo, estilo) => ({ lista, campo, estilo,
  get titulo() { return t('dim_' + k); }, get sem() { return t('sem_' + k); }, get desc() { return t('dimdesc_' + k); } });
const DIMS = {
  comunidades: dimDe('comunidades', D.comunidades, 'comunidades', 'solid'),
  temas: dimDe('temas', D.temas, 'temas', 'dashed'),
  atuacao: dimDe('atuacao', D.atuacoes, 'atuacao', 'label')
};
const gColor = {}, gName = {};
function nomearGrupos() {   // nomes no idioma atual (nome_en vem dos dados)
  for (const k in DIMS) {
    gColor[k] = {}; gName[k] = {};
    DIMS[k].lista.forEach((g, i) => { gColor[k][g.id] = PAL[i % PAL.length]; gName[k][g.id] = nomeDe(g); });
    gColor[k][SEM] = NEUTRAL; gName[k][SEM] = DIMS[k].sem;
  }
}
nomearGrupos();
const papelPorId = Object.fromEntries(D.papeis.map(p => [p.id, p]));
// áreas = comunidades + temas (usadas no mural e nas iniciativas). O valor guardado é sempre o nome em PT.
const AREAS = D.comunidades.map(c => ({ nome: c.nome, tipo: 'comunidades', id: c.id }))
  .concat(D.temas.map(x => ({ nome: x.nome, tipo: 'temas', id: x.id })));
const areaPorNome = Object.fromEntries(AREAS.map(a => [a.nome, a]));
const nomeArea = n => { const a = areaPorNome[n]; return a ? gName[a.tipo][a.id] : n; };

let dim = 'comunidades', filtro = null, selId = null, view = 'pessoas', g3 = null, mode3d = 'pessoas';
const hidden = new Set();   // saídas pedidas nesta sessão (não persiste: some ao recarregar até a próxima atualização)
const pessoas = () => D.pessoas.filter(p => !hidden.has(p.id));
const byId = Object.fromEntries(D.pessoas.map(p => [p.id, p]));
const grupos = (p, d = dim) => (p[DIMS[d].campo] || []).length ? p[DIMS[d].campo] : [SEM];
const areasDaPessoa = p => new Set([...(p.comunidades || []).map(c => D.comunidades.find(x => x.id === c)?.nome), ...(p.temas || []).map(x => D.temas.find(y => y.id === x)?.nome)]);

function orgs() {
  const m = {};
  pessoas().forEach(p => {
    if (!p.organizacao) return;
    const id = 'o:' + slug(p.organizacao);
    (m[id] ||= { id, nome: p.organizacao, membros: [] }).membros.push(p.id);
  });
  return Object.values(m).map(o => Object.assign(o, {
    g: d => { const s = new Set(); o.membros.forEach(id => grupos(byId[id], d).forEach(x => s.add(x))); if (s.size > 1) s.delete(SEM); return s; }
  }));
}
const orgById = () => Object.fromEntries(orgs().map(o => [o.id, o]));
function counts() { const c = {}; pessoas().forEach(p => grupos(p).forEach(g => c[g] = (c[g] || 0) + 1)); return c; }
let CNT = counts();
function hubs(used) {
  return DIMS[dim].lista.filter(g => used.has(g.id)).map(g => ({ id: 'g:' + g.id, tipo: 'com', com: g.id, nome: gName[dim][g.id] }))
    .concat(used.has(SEM) ? [{ id: 'g:' + SEM, tipo: 'com', com: SEM, nome: DIMS[dim].sem }] : []);
}
function graphPessoas() {
  const ps = pessoas(), ids = new Set(ps.map(p => p.id)), used = new Set();
  ps.forEach(p => grupos(p).forEach(g => used.add(g)));
  const nodes = hubs(used).concat(ps.map(p => ({ id: p.id, tipo: 'p', p, com: grupos(p)[0], nome: p.nome })));
  const links = [];
  ps.forEach(p => grupos(p).forEach(g => links.push({ source: p.id, target: 'g:' + g, tipo: 'pc', com: g })));
  D.ligacoes.forEach(l => { if (ids.has(l.a) && ids.has(l.b)) links.push({ source: l.a, target: l.b, tipo: 'pp' }); });
  return { nodes, links };
}
function graphOrgs() {
  const os = orgs(), used = new Set(); os.forEach(o => o.g(dim).forEach(g => used.add(g)));
  const nodes = hubs(used).concat(os.map(o => ({ id: o.id, tipo: 'o', o, com: [...o.g(dim)][0], nome: o.nome })));
  const links = []; os.forEach(o => o.g(dim).forEach(g => links.push({ source: o.id, target: 'g:' + g, tipo: 'pc', com: g })));
  return { nodes, links };
}
const graph3d = () => mode3d === 'orgs' ? graphOrgs() : graphPessoas();
const color = n => gColor[dim][n.com] || NEUTRAL;
function visible(n) {
  if (!filtro) return true;
  if (n.tipo === 'com') return n.com === filtro;
  if (n.tipo === 'p') return grupos(n.p).includes(filtro);
  if (n.tipo === 'o') return n.o.g(dim).has(filtro);
  return true;
}

// ---------------------------------------------------------------- 2D (d3-force)
function make2D(el, build) {
  const st = {};
  st.build = () => {
    el.innerHTML = ''; const { nodes, links } = build(); st.nodes = nodes;
    const W = el.clientWidth || 900, H = el.clientHeight || 600;
    const svg = d3.select(el).append('svg').attr('role', 'img').attr('aria-label', t('mapa_aria')), g = svg.append('g'); st.svg = svg;
    st.zoom = d3.zoom().scaleExtent([.3, 4]).on('zoom', e => g.attr('transform', e.transform));
    svg.call(st.zoom).on('click', e => { if (e.target.tagName === 'svg') closeCard(); });
    st.link = g.append('g').selectAll('line').data(links).join('line')
      .attr('stroke', d => d.tipo === 'pp' ? '#2A1C13' : gColor[dim][d.com]).attr('stroke-opacity', d => d.tipo === 'pp' ? .55 : .25)
      .attr('stroke-width', d => d.tipo === 'pp' ? 1.6 : 1).attr('stroke-dasharray', d => d.tipo === 'pp' ? '4 3' : null);
    const est = DIMS[dim].estilo;
    nodes.forEach(d => { d.rad = d.tipo === 'com' ? (est === 'label' ? 10 : 16 + Math.sqrt(CNT[d.com] || 1) * 3) : d.tipo === 'o' ? 6 + Math.sqrt(d.o.membros.length) * 3 : 7; });
    st.node = g.append('g').selectAll('path').data(nodes).join('path')
      .attr('d', d => d3.symbol(d3.symbolCircle, Math.PI * d.rad * d.rad)())
      .style('cursor', 'pointer').attr('stroke', color)
      .attr('stroke-width', d => d.tipo === 'com' ? (est === 'label' ? 0 : 2) : 2.5)
      .attr('stroke-dasharray', d => d.tipo === 'com' && (est === 'dashed' || d.com === SEM) ? '6 4' : null)
      .attr('fill', d => d.tipo === 'com' ? gColor[dim][d.com] : '#FFFBF4')
      .attr('fill-opacity', d => d.tipo === 'com' ? (est === 'solid' && d.com !== SEM ? .18 : est === 'label' ? .001 : .05) : 1)
      .on('click', (e, d) => { e.stopPropagation(); if (d.tipo === 'com') setFiltro(d.com); else select(d.id); })
      .call(d3.drag().on('start', (e, d) => { if (!e.active) st.sim.alphaTarget(.2).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; }).on('end', (e, d) => { if (!e.active) st.sim.alphaTarget(0); d.fx = null; d.fy = null; }));
    st.node.append('title').text(d => d.tipo === 'o' ? `${d.nome} · ${t('n_pessoas', d.o.membros.length)}` : d.nome);
    st.lbl = g.append('g').selectAll('text').data(nodes).join('text')
      .attr('class', d => d.tipo === 'com' ? 'comlbl' : 'lbl').attr('text-anchor', 'middle')
      .attr('fill', d => d.tipo === 'com' ? gColor[dim][d.com] : null).style('font-size', d => d.tipo === 'com' && est === 'label' ? '17px' : null)
      .text(d => d.tipo === 'p' ? d.nome.split(' ').slice(0, 2).join(' ') : d.nome);
    let fitted = false;
    st.sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(d => d.tipo === 'pp' ? 70 : 95).strength(d => d.tipo === 'pp' ? .15 : .5))
      .force('charge', d3.forceManyBody().strength(d => d.tipo === 'com' ? -1400 : -170))
      .force('collide', d3.forceCollide(d => d.tipo === 'com' ? 55 : d.rad + 12))
      .force('center', d3.forceCenter(W / 2, H / 2)).force('x', d3.forceX(W / 2).strength(.04)).force('y', d3.forceY(H / 2).strength(.04))
      .on('tick', () => {
        st.link.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y);
        st.node.attr('transform', d => `translate(${d.x},${d.y})`);
        st.lbl.attr('x', d => d.x).attr('y', d => d.tipo === 'com' ? d.y + 4 : d.y + d.rad + 12);
      }).on('end', () => { if (!fitted) { fitted = true; st.fit(); } });
    st.refresh();
  };
  st.fit = () => {
    const ns = st.nodes; if (!ns || !ns.length || !el.clientWidth) return;
    const x0 = d3.min(ns, d => d.x) - 60, x1 = d3.max(ns, d => d.x) + 60, y0 = d3.min(ns, d => d.y) - 40, y1 = d3.max(ns, d => d.y) + 40;
    const k = Math.min(1.4, el.clientWidth / (x1 - x0), el.clientHeight / (y1 - y0));
    st.svg.transition().duration(700).call(st.zoom.transform, d3.zoomIdentity.translate(el.clientWidth / 2, el.clientHeight / 2).scale(k).translate(-(x0 + x1) / 2, -(y0 + y1) / 2));
  };
  st.refresh = () => {
    if (!st.node) return;
    const nb = new Set(); if (selId) { nb.add(selId); D.ligacoes.forEach(l => { if (l.a === selId) nb.add(l.b); if (l.b === selId) nb.add(l.a); }); }
    st.node.attr('opacity', d => visible(d) ? 1 : .08).attr('fill', d => d.tipo === 'com' ? gColor[dim][d.com] : (d.id === selId ? color(d) : '#FFFBF4'));
    st.lbl.attr('opacity', d => visible(d) ? (selId && d.tipo !== 'com' && !nb.has(d.id) ? .35 : 1) : .05).style('font-weight', d => d.id === selId ? '700' : null);
    st.link.attr('opacity', d => { if (!(visible(d.source) && visible(d.target))) return .03; if (selId && d.tipo === 'pp') return (d.source.id === selId || d.target.id === selId) ? 1 : .25; return 1; });
  };
  st.focus = id => {
    const n = (st.nodes || []).find(x => x.id === id); if (!n || n.x == null) return;
    st.svg.transition().duration(600).call(st.zoom.transform, d3.zoomIdentity.translate(el.clientWidth / 2, el.clientHeight / 2).scale(1.6).translate(-n.x, -n.y));
  };
  return st;
}
const V = { pessoas: make2D($('vPessoas'), graphPessoas), orgs: make2D($('vOrgs'), graphOrgs) };

// ---------------------------------------------------------------- 3D (mesma lib e visual do Atria)
function init3D() {
  return new Promise((res, rej) => {
    const s = document.createElement('script');
    s.src = 'vendor/3d-force-graph.min.js';
    s.onerror = () => { $('view3d').innerHTML = `<p style="color:#ccc;padding:24px">${t('erro_3d')}</p>`; res(); };
    s.onload = () => {
      const el = $('view3d');
      g3 = ForceGraph3D()(el).backgroundColor('#000000').width(el.clientWidth).height(el.clientHeight).nodeId('id')
        .nodeLabel(n => n.tipo === 'com' ? esc(n.nome) : n.tipo === 'o'
          ? `${esc(n.nome)} · ${t('n_pessoas', n.o.membros.length)} — ${[...n.o.g(dim)].map(c => esc(gName[dim][c])).join(', ')}`
          : `${esc(n.nome)}${n.p.organizacao ? ' · ' + esc(n.p.organizacao) : ''} — ${grupos(n.p).map(c => esc(gName[dim][c])).join(', ')}`)
        .nodeColor(n => n.id === selId ? '#ffffff' : color(n))
        .nodeVal(n => n.tipo === 'com' ? 3 : (n.id === selId ? 4 : (n.tipo === 'o' ? 1.2 + n.o.membros.length * .8 : 1.6)))
        .nodeOpacity(.9)
        .linkColor(l => l.tipo === 'pp' ? 'rgba(255,255,255,0.75)' : 'rgba(255,255,255,0.22)')
        .linkOpacity(.35).linkWidth(l => l.tipo === 'pp' ? 1 : 0)
        .onNodeClick(n => { if (n.tipo === 'com') setFiltro(n.com); else select(n.id); })
        .onBackgroundClick(closeCard)
        .graphData(graph3d());
      res();
    };
    document.head.appendChild(s);
  });
}
function refresh3D() { if (!g3) return; g3.nodeVisibility(visible).linkVisibility(l => visible(l.source) && visible(l.target)).nodeColor(g3.nodeColor()).nodeVal(g3.nodeVal()); }

// ---------------------------------------------------------------- lateral, estatísticas, busca
function sidebar() {
  CNT = counts(); const d = DIMS[dim];
  $('dimdesc').textContent = d.desc; $('dimtitle').textContent = d.titulo;
  const items = d.lista.filter(g => CNT[g.id]).sort((a, b) => CNT[b.id] - CNT[a.id]).map(g => ({ id: g.id, nome: gName[dim][g.id] }));
  if (CNT[SEM]) items.push({ id: SEM, nome: d.sem });
  const cls = d.estilo === 'solid' ? '' : d.estilo;
  $('coms').innerHTML = items.map(g => `<button class="com${g.id === filtro ? ' on' : ''}" data-c="${g.id}" style="color:${gColor[dim][g.id]}"><span class="dot ${g.id === SEM ? 'dashed' : cls}" style="background:${gColor[dim][g.id]}"></span><span style="color:var(--ink)">${esc(g.nome)}</span><span class="n">${CNT[g.id]}</span></button>`).join('');
  document.querySelectorAll('.com').forEach(b => b.onclick = () => setFiltro(b.dataset.c));
}
function setFiltro(c) { filtro = filtro === c ? null : c; document.querySelectorAll('.com').forEach(x => x.classList.toggle('on', x.dataset.c === filtro)); refresh(); }
function stats() {
  const ps = pessoas(), ids = new Set(ps.map(p => p.id)), lig = D.ligacoes.filter(l => ids.has(l.a) && ids.has(l.b));
  const con = new Set(); lig.forEach(l => { con.add(l.a); con.add(l.b); });
  const pct = ps.length ? Math.round(100 * con.size / ps.length) : 0;
  $('stats').innerHTML = t('stats', { p: ps.length, o: orgs().length, c: D.comunidades.length, t: D.temas.length, l: lig.length, pct });
  $('nomes').innerHTML = ps.map(p => `<option value="${esc(p.nome)}">`).join('') + orgs().map(o => `<option value="${esc(o.nome)}">${t('organizacao')}</option>`).join('');
  const ab = D.mural.filter(m => m.status === 'aberto').length, at = D.iniciativas.filter(i => i.status === 'ativa').length;
  $('cntMural').textContent = ab || ''; $('cntIni').textContent = at || '';
}
const semAcento = s => String(s || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
function buscar(v, aproximado) {
  const k = semAcento(v); if (!k) return false;
  const ps = pessoas(), os = orgs();
  const achar = (lista, f) => lista.find(x => f(semAcento(x.nome)));
  const hit = achar(ps, n => n === k) || achar(os, n => n === k) ||
    (aproximado && (achar(ps, n => n.startsWith(k)) || achar(ps, n => n.includes(k)) || achar(os, n => n.includes(k))));
  if (hit) { select(hit.id, true); return true; }
  return false;
}
$('q').addEventListener('change', e => buscar(e.target.value, false));
$('q').addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); if (!buscar(e.target.value, true)) e.target.setCustomValidity(t('busca_nada')), e.target.reportValidity(), setTimeout(() => e.target.setCustomValidity(''), 1500); } });
$('seg').querySelectorAll('button').forEach(b => b.onclick = () => {
  dim = b.dataset.d; filtro = null;
  $('seg').querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); sidebar(); rebuild();
});

// ---------------------------------------------------------------- card
const tinta = hex => { const n = parseInt(hex.slice(1), 16), r = n >> 16, g = (n >> 8) & 255, b = n & 255;
  return (0.299 * r + 0.587 * g + 0.114 * b) > 150 ? '#2A1C13' : '#fff'; };
const chipsCom = cs => `<div class="chips">${cs.map(c => `<span class="chip" style="background:${gColor.comunidades[c]};color:${tinta(gColor.comunidades[c])}">${esc(gName.comunidades[c])}</span>`).join('')}</div>`;
const chipsTema = ts => `<div class="chips">${ts.map(t => `<span class="chip outline" style="border-color:${gColor.temas[t]}">${esc(gName.temas[t])}</span>`).join('')}</div>`;
const chipsArea = as => `<div class="chips">${as.map(n => { const a = areaPorNome[n]; if (!a) return `<span class="chip soft">${esc(n)}</span>`;
  return a.tipo === 'comunidades' ? `<span class="chip" style="background:${gColor.comunidades[a.id]};color:${tinta(gColor.comunidades[a.id])}">${esc(nomeArea(n))}</span>` : `<span class="chip outline" style="border-color:${gColor.temas[a.id]}">${esc(nomeArea(n))}</span>`; }).join('')}</div>`;
const pessoaLink = id => byId[id] && !hidden.has(id) ? `<button class="linkbtn" data-pessoa="${esc(id)}">${esc(byId[id].nome)}</button>` : '';
const blocos = (cs, ts, as) => `
  <div class="blk"><h4>${t('dim_comunidades')}</h4>${cs.length ? chipsCom(cs) : `<p class="none">${t('sem_comunidades')}</p>`}</div>
  <div class="blk"><h4>${t('dim_temas')}</h4>${ts.length ? chipsTema(ts) : '<p class="none">—</p>'}</div>
  <div class="blk"><h4>${t('dim_atuacao')}</h4>${as.length ? `<p class="plain">${as.map(a => esc(gName.atuacao[a])).join(' · ')}</p>` : '<p class="none">—</p>'}</div>`;

function cardPessoa(p) {
  const papeis = (p.papeis || []).map(id => papelPorId[id]).filter(Boolean);
  const conhecer = (p.conhecer || []).filter(c => byId[c.id] && !hidden.has(c.id));
  const meus = D.mural.filter(m => m.autor_id === p.id);
  const inis = D.iniciativas.filter(i => i.proponente_id === p.id || (i.participantes || []).includes(p.id));
  const perfil = [[t('pode_compartilhar'), p.compartilha], [t('quer_aprender'), p.aprende], [t('toparia_convocar'), p.convoca]].filter(x => x[1]);
  return `<p class="kind">${t('pessoa')}</p><h3>${esc(p.nome)}</h3>
    ${papeis.length ? `<div class="badges">${papeis.map(x => `<span class="badge" title="${esc(window.I18N.desc(x))}">${esc(nomeDe(x))}</span>`).join('')}</div>` : ''}
    <p class="role">${esc([p.cargo, p.organizacao].filter(Boolean).join(' · '))}</p>
    ${blocos(p.comunidades || [], p.temas || [], p.atuacao || [])}
    ${perfil.map(([t, v]) => `<div class="blk"><h4>${t}</h4><p class="plain">${esc(v)}</p></div>`).join('')}
    ${meus.length ? `<div class="blk"><h4>${t('no_mural')}</h4><ul class="people">${meus.map(m => `<li><button class="linkbtn" data-item="${esc(m.id)}">${m.tipo === 'oferta' ? t('oferece') : t('pede')}: ${esc(m.titulo)}</button></li>`).join('')}</ul></div>` : ''}
    ${inis.length ? `<div class="blk"><h4>${t('ini_titulo')}</h4><ul class="people">${inis.map(i => `<li><button class="linkbtn" data-ini="${esc(i.id)}">${esc(i.titulo)}</button></li>`).join('')}</ul></div>` : ''}
    ${conhecer.length ? `<div class="blk"><h4>${t('conhecer')}</h4><ul class="people">${conhecer.map(c => `<li>${pessoaLink(c.id)}<small>${t('em_comum')}: ${[...(c.temas || []).map(t => gName.temas[t] || t), ...(c.comunidades || []).map(x => gName.comunidades[x] || x)].map(esc).join(', ')}</small></li>`).join('')}</ul></div>` : ''}
    ${/^https?:\/\//i.test(p.linkedin || '') ? `<a class="li" href="${esc(p.linkedin)}" target="_blank" rel="noopener">${t('ver_linkedin')}</a>` : ''}
    <div class="actions"><button class="btn sm" data-acao="conheco">${t('conheco')}</button></div>
    <div class="stay" id="stay"><p class="q">${t('e_voce')}</p>
      <div class="opts"><button class="btn sm" data-acao="perfil">${t('atualizar_perfil')}</button><button class="btn sm line" data-acao="ficar">${t('ficar')}</button><button class="btn sm line" data-acao="sair">${t('sair')}</button></div></div>`;
}
function cardOrg(o) {
  const g = d => [...o.g(d)].filter(x => x !== SEM);
  return `<p class="kind">${t('organizacao')}</p><h3>${esc(o.nome)}</h3><p class="role">${t('n_na_rede', o.membros.length)}</p>
    ${blocos(g('comunidades'), g('temas'), g('atuacao'))}
    <div class="blk"><h4>${t('tab_pessoas')}</h4><ul class="people">${o.membros.map(m => `<li>${pessoaLink(m)}<small>${esc(byId[m].cargo || '')}</small></li>`).join('')}</ul></div>`;
}
function select(id, center) {
  const isOrg = id.startsWith('o:');
  if (view === 'orgs' && !isOrg) { selId = null; switchView('pessoas'); }
  if (view === 'pessoas' && isOrg) { selId = null; switchView('orgs'); }
  if (view === '3d' && (mode3d === 'orgs') !== isOrg) {
    mode3d = isOrg ? 'orgs' : 'pessoas';
    $('t3d').querySelectorAll('button').forEach(x => x.classList.toggle('on', x.dataset.m === mode3d));
    if (g3) g3.graphData(graph3d());
  }
  selId = id;
  if (isOrg) { const o = orgById()[id]; if (!o) return; $('cBody').innerHTML = cardOrg(o); }
  else { const p = byId[id]; if (!p) return; $('cBody').innerHTML = cardPessoa(p); }
  $('card').classList.add('show'); refresh();
  if (center && V[view]) V[view].focus(id);
  setHash(isOrg ? (view === 'pessoas' ? '' : view) : 'p/' + id);
}
function closeCard() { selId = null; $('card').classList.remove('show'); refresh(); if (location.hash.startsWith('#p/')) setHash(view === 'pessoas' ? '' : view); }
window.closeCard = closeCard;
document.addEventListener('keydown', e => { if (e.key === 'Escape' && !dlg.open && $('card').classList.contains('show')) closeCard(); });
$('cBody').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  if (b.dataset.pessoa) return select(b.dataset.pessoa, true);
  if (b.dataset.item) return irPara('mural', b.dataset.item);
  if (b.dataset.ini) return irPara('iniciativas', b.dataset.ini);
  const p = byId[selId];
  ({ conheco: () => dlgConheco(p), perfil: () => dlgPerfil(p), ficar: () => ficar(p), sair: () => perguntarSair(p) }[b.dataset.acao] || (() => {}))();
});

// ---------------------------------------------------------------- envio de formulários (Netlify Forms)
async function enviar(form, campos) {
  if (LOCAL) return 'local';
  try {
    const r = await fetch('/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ 'form-name': form, ...campos }).toString() });
    return r.ok ? 'ok' : 'erro';
  } catch (e) { return 'erro'; }
}
const RESULT = {
  ok: m => `<p class="ok">${m}</p>`,
  local: () => `<p class="local">${t('res_local')}</p>`,
  erro: () => `<p class="local">${t('res_erro')}</p>`
};
const dlg = $('dlg');
function abrir(html, aoMontar) { $('dlgBody').innerHTML = html; if (!dlg.open) dlg.showModal(); if (aoMontar) aoMontar($('dlgBody')); }
function fechar() { dlg.close(); }
window.fechar = fechar;
dlg.addEventListener('click', e => { if (e.target === dlg) fechar(); });
function formulario(nomeForm, titulo, intro, corpo, botao, sucesso, prep) {
  abrir(`<form id="fx" novalidate><h3 id="dlgTitle">${titulo}</h3>${intro ? `<p>${intro}</p>` : ''}${corpo}
    <p hidden><label>${t('nao_preencha')} <input name="bot" tabindex="-1" autocomplete="off"></label></p>
    <div id="fxMsg"></div>
    <div class="row"><button type="button" class="btn ghost" onclick="fechar()">${t('cancelar')}</button><button class="btn" type="submit">${botao}</button></div></form>`,
  el => {
    el.querySelectorAll('textarea[maxlength]').forEach(t => {
      const c = document.createElement('div'); c.className = 'counter'; t.after(c);
      const up = () => c.textContent = `${t.value.length}/${t.maxLength}`; t.addEventListener('input', up); up();
    });
    el.querySelector('#fx').addEventListener('submit', async e => {
      e.preventDefault();
      const f = e.target, msg = el.querySelector('#fxMsg');
      const campos = {}; new FormData(f).forEach((v, k) => { campos[k] = campos[k] ? campos[k] + '; ' + v : v; });
      const erro = prep ? prep(campos, f) : null;
      if (erro) { msg.innerHTML = `<p class="local">${erro}</p>`; return; }
      const r = await enviar(nomeForm, campos);
      f.querySelector('.row').innerHTML = `<button type="button" class="btn" onclick="fechar()">${t('fechar')}</button>`;
      msg.innerHTML = r === 'ok' ? RESULT.ok(sucesso) : RESULT[r]();
      f.querySelectorAll('input,textarea,select').forEach(x => x.disabled = true);
    });
  });
}
const PRIV = () => `<p class="privacy">${t('priv')}</p>`;
const req = (campos, nomes) => { for (const [k, rot] of nomes) if (!String(campos[k] || '').trim()) return t('preencha', t(rot)); return null; };
const dica = k => ` <small>${t(k)}</small>`;
function seletorAreas(max = 3) {
  return `<div class="areas" data-max="${max}">${AREAS.map(a => `<label><input type="checkbox" name="areas" value="${esc(a.nome)}"> ${esc(nomeArea(a.nome))}</label>`).join('')}</div>
`;
}
function limitarAreas(el) {
  const box = el.querySelector('.areas'); if (!box) return;
  box.addEventListener('change', () => {
    const marc = box.querySelectorAll('input:checked'), max = +box.dataset.max;
    box.querySelectorAll('input').forEach(i => i.disabled = !i.checked && marc.length >= max);
  });
}
const opcoesPessoas = () => `<datalist id="dlPessoas">${pessoas().slice().sort((a, b) => a.nome.localeCompare(b.nome)).map(p => `<option value="${esc(p.nome)}">`).join('')}</datalist>`;

function dlgConheco(p) {
  formulario('sugestao-ligacao', t('conheco'), t('conheco_intro', esc(p.nome)),
    `<input type="hidden" name="pessoa" value="${esc(p.nome)}">
     <label>${t('quem_e_voce')}${dica('quem_e_voce_dica')}</label><input name="quem_sugere" list="dlPessoas" required>${opcoesPessoas()}
     <label>${t('como_conhecem')}${dica('opcional')}</label><textarea name="contexto" rows="2" maxlength="300"></textarea>`,
    t('enviar'), t('conheco_ok'), c => req(c, [['quem_sugere', 'r_quem']]));
}
function dlgPerfil(p) {
  formulario('perfil', t('atualizar_perfil'), t('perfil_intro'),
    `<input type="hidden" name="pessoa" value="${esc(p.nome)}">
     <label>${t('p_compartilha')}${dica('p_compartilha_dica')}</label><textarea name="compartilha" rows="2" maxlength="200"></textarea>
     <label>${t('p_aprende')}</label><textarea name="aprende" rows="2" maxlength="200"></textarea>
     <label>${t('p_convoca')}</label><input name="convocaria" maxlength="200">
     <label>${t('p_colabora')}${dica('p_colabora_dica')}</label><input name="colabora_com" list="dlPessoas">
     <label>${t('p_gostaria')}${dica('p_gostaria_dica')}</label><input name="gostaria_colaborar" list="dlPessoas">${opcoesPessoas()}
     <label>${t('seu_contato')}${dica('p_contato_dica')}</label><input name="contato">
     ${PRIV()}<p class="privacy">${esc(t('p_priv'))}</p>`,
    t('enviar'), t('perfil_ok'),
    c => (c.compartilha || c.aprende || c.convocaria || c.colabora_com || c.gostaria_colaborar) ? null : t('perfil_min'));
}
function ficar(p) { enviar('opt-in', { nome: p.nome }).then(r => { $('stay').innerHTML = r === 'local' ? RESULT.local() : `<p class="done">${t('ficar_ok')}</p>`; }); }
function perguntarSair(p) {
  $('stay').innerHTML = `<p class="q"><b>${t('sair_q')}</b> ${t('sair_q_txt')}</p>
    <div class="opts"><button class="btn sm" id="simSair">${t('sim')}</button><button class="btn sm line" id="naoSair">${t('nao')}</button></div>`;
  $('simSair').onclick = () => confirmarSaida(p.id, 'card');
  $('naoSair').onclick = () => select(p.id);
}
async function confirmarSaida(id, origem) {
  const r = await enviar('opt-out', { nome: byId[id].nome, origem });
  hidden.add(id); closeCard(); rebuild();
  abrir(`<h3>${t('saida_titulo')}</h3><p>${t('saida_txt')}</p>${r === 'local' ? RESULT.local() : ''}
    <div class="row"><button class="btn" onclick="fechar()">${t('fechar')}</button></div>`);
}
function dlgSair() {
  abrir(`<h3 id="dlgTitle">${t('sair_link')}</h3><p>${t('sair_intro')}</p>
    <label for="oSel">${t('seu_nome')}</label><select id="oSel"><option value="">${t('selecione')}</option>${pessoas().slice().sort((a, b) => a.nome.localeCompare(b.nome)).map(p => `<option value="${esc(p.id)}">${esc(p.nome)}</option>`).join('')}</select>
    <div id="oStep" class="row"><button class="btn ghost" onclick="fechar()">${t('cancelar')}</button><button class="btn" id="oCont">${t('continuar')}</button></div>`,
  el => {
    el.querySelector('#oCont').onclick = () => {
      const id = el.querySelector('#oSel').value; if (!id) return;
      el.querySelector('#oStep').outerHTML = `<p style="margin-top:14px"><b>${t('sair_q')}</b></p><div class="row"><button class="btn ghost" onclick="fechar()">${t('nao')}</button><button class="btn" id="oSim">${t('sim')}</button></div>`;
      el.querySelector('#oSim').onclick = () => confirmarSaida(id, 'rodape');
    };
  });
}
$('lnkSair').onclick = e => { e.preventDefault(); dlgSair(); };
function dlgSobre() {
  const s = D.sobre || { responsavel: '', contato: null };
  abrir(`<h3 id="dlgTitle">${t('sobre_link')}</h3><div class="sobre">${t('sobre_html', { responsavel: esc(s.responsavel), contato: s.contato ? esc(s.contato) : '' })}</div>
    <div class="row"><button class="btn" onclick="fechar()">${t('fechar')}</button></div>`);
}
$('lnkSobre').onclick = e => { e.preventDefault(); dlgSobre(); };

// ---------------------------------------------------------------- mural
let fMural = '';
function quemTrabalhaCom(areas, exceto) {
  const alvo = new Set(areas);
  return pessoas().filter(p => p.id !== exceto).map(p => ({ p, n: [...areasDaPessoa(p)].filter(a => alvo.has(a)).length }))
    .filter(x => x.n).sort((a, b) => b.n - a.n || a.p.nome.localeCompare(b.p.nome)).slice(0, 4).map(x => x.p);
}
const diasDesde = data => data ? Math.round((Date.now() - new Date(data + 'T12:00:00')) / 864e5) : 0;
async function copiarLink(b) {
  const url = location.href.split('#')[0] + '#' + b.dataset.link;
  try { await navigator.clipboard.writeText(url); b.textContent = t('link_copiado'); }
  catch (e) { window.prompt(t('copie_link'), url); }
  setTimeout(() => b.textContent = t('copiar_link'), 1600);
}
function renderMural() {
  const area = $('fMuralArea').value, q = $('fMuralQ').value.trim().toLowerCase(), atend = $('fMuralAtendidos').checked;
  const itens = D.mural.filter(m => (!fMural || m.tipo === fMural) && (!area || m.areas.includes(area)) && (atend || m.status === 'aberto')
    && (!m.autor_id || !hidden.has(m.autor_id))
    && (!q || (m.titulo + ' ' + m.descricao + ' ' + (m.autor || '')).toLowerCase().includes(q)));
  if (!itens.length) {
    const nada = !D.mural.length;
    $('muralGrid').innerHTML = `<div class="empty"><h3>${nada ? t('mural_vazio_t') : t('nada_filtros')}</h3>
      <p>${nada ? t('mural_vazio_p') : t('mural_nada_p')}</p>
      ${nada ? `<div class="steps">${[1, 2, 3].map(i => `<div class="step"><b>${t(`passo${i}_t`)}</b>${t(`passo${i}`)}</div>`).join('')}</div>` : ''}
      <button class="btn" onclick="dlgPublicar()">${t('btn_publicar')}</button></div>`;
    return;
  }
  $('muralGrid').innerHTML = itens.map(m => {
    const match = m.tipo === 'pedido' && m.status === 'aberto' ? quemTrabalhaCom(m.areas, m.autor_id) : [];
    const autor = m.autor_id && byId[m.autor_id] ? pessoaLink(m.autor_id) : esc(m.autor || t('alguem'));
    return `<article class="item${m.status === 'atendido' ? ' fechado' : ''}" id="item-${esc(m.id)}">
      <div class="top"><span class="tag ${m.tipo}">${m.tipo === 'oferta' ? t('oferta') : t('pedido')}</span>${m.status === 'atendido' ? `<span class="tag gray">${t('atendido')}</span>` : ''}</div>
      <h3>${esc(m.titulo)}</h3>${m.descricao ? `<p>${esc(m.descricao)}</p>` : ''}
      ${m.areas.length ? chipsArea(m.areas) : ''}
      <p class="meta">${autor} · ${quando(m.data)}${m.status === 'aberto' && diasDesde(m.data) > 60 ? ` · <span title="${t('antigo_title')}">${t('antigo')}</span>` : ''}</p>
      ${match.length ? `<p class="match">${t('quem_trabalha')} ${match.map(p => pessoaLink(p.id)).join(', ')}</p>` : ''}
      ${m.status === 'aberto' ? `<div class="foot"><button class="btn sm" data-responder="${esc(m.id)}">${m.tipo === 'pedido' ? t('posso_ajudar') : t('tenho_interesse')}</button><button class="btn sm line" data-link="m/${esc(m.id)}">${t('copiar_link')}</button></div>` : ''}
    </article>`;
  }).join('');
}
$('muralGrid').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  if (b.dataset.pessoa) return select(b.dataset.pessoa);
  if (b.dataset.link) return copiarLink(b);
  if (b.dataset.responder) dlgResponder(D.mural.find(m => m.id === b.dataset.responder));
});
$('segMural').querySelectorAll('button').forEach(b => b.onclick = () => { fMural = b.dataset.f; $('segMural').querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); renderMural(); });
['fMuralArea', 'fMuralAtendidos'].forEach(id => $(id).addEventListener('change', renderMural));
$('fMuralQ').addEventListener('input', renderMural);
function dlgPublicar(tipo) {
  formulario('mural', t('publicar_t'), t('publicar_intro'),
    `<label>${t('voce_quer')}</label><div class="radios"><label><input type="radio" name="tipo" value="Oferta" ${tipo !== 'Pedido' ? 'checked' : ''}> ${t('oferecer')}</label><label><input type="radio" name="tipo" value="Pedido" ${tipo === 'Pedido' ? 'checked' : ''}> ${t('pedir')}</label></div>
     <label>${t('titulo_l')}</label><input name="titulo" maxlength="90" required placeholder="${esc(t('titulo_ph'))}">
     <label>${t('descricao')}</label><textarea name="descricao" rows="3" maxlength="420"></textarea>
     <label>${t('areas')}${dica('ate_3')}</label>${seletorAreas(3)}
     <label>${t('seu_nome')}${dica('nome_mural_dica')}</label><input name="nome" required>
     <label>${t('no_mapa')}${dica('no_mapa_dica')}</label><input name="no_mapa" list="dlPessoas">${opcoesPessoas()}
     <label>${t('seu_contato')}${dica('contato_dica')}</label><input name="contato" required>
     ${PRIV()}
     <label class="consent"><input type="checkbox" name="consentimento" value="sim"> ${t('consent_mural')}</label>`,
    t('enviar_revisao'), t('publicar_ok'),
    c => req(c, [['titulo', 'r_titulo'], ['nome', 'r_nome'], ['contato', 'r_contato']]) || (c.consentimento ? null : t('concordancia')));
  limitarAreas($('dlgBody'));
}
window.dlgPublicar = dlgPublicar;
$('btnPublicar').onclick = () => dlgPublicar();
function dlgResponder(m) {
  formulario('mural-resposta', m.tipo === 'pedido' ? t('posso_ajudar') : t('tenho_interesse'), t('responder_intro', esc(m.titulo)),
    `<input type="hidden" name="item_id" value="${esc(m.id)}"><input type="hidden" name="item_titulo" value="${esc(m.titulo)}">
     <label>${t('seu_nome')}</label><input name="nome" required list="dlPessoas">${opcoesPessoas()}
     <label>${t('seu_contato')}${dica('contato_dica')}</label><input name="contato" required>
     <label>${t('mensagem')}${dica('mensagem_dica')}</label><textarea name="mensagem" rows="3" maxlength="500"></textarea>${PRIV()}`,
    t('enviar'), t('responder_ok'), c => req(c, [['nome', 'r_nome'], ['contato', 'r_contato']]));
}

// ---------------------------------------------------------------- iniciativas
let fIni = '';
function renderIni() {
  const area = $('fIniArea').value, concl = $('fIniConcluidas').checked;
  const itens = D.iniciativas.filter(i => (!fIni || i.tipo === fIni) && (!area || i.areas.includes(area)) && (concl || i.status === 'ativa'));
  if (!itens.length) {
    const nada = !D.iniciativas.length;
    $('iniGrid').innerHTML = `<div class="empty"><h3>${nada ? t('ini_vazio_t') : t('nada_filtros')}</h3>
      <p>${nada ? t('ini_vazio_p') : t('ini_nada_p')}</p>
      <button class="btn" onclick="dlgPropor()">${t('btn_propor')}</button></div>`;
    return;
  }
  $('iniGrid').innerHTML = itens.map(i => {
    const part = (i.participantes || []).filter(id => byId[id] && !hidden.has(id));
    const prop = i.proponente_id && byId[i.proponente_id] ? pessoaLink(i.proponente_id) : esc(i.proponente || '');
    return `<article class="item${i.status !== 'ativa' ? ' fechado' : ''}" id="ini-${esc(i.id)}">
      <div class="top"><span class="tag ini">${esc(t('tipo:' + i.tipo))}</span>${i.status !== 'ativa' ? `<span class="tag gray">${t('concluida')}</span>` : ''}</div>
      <h3>${esc(i.titulo)}</h3>${i.descricao ? `<p>${esc(i.descricao)}</p>` : ''}
      ${i.areas.length ? chipsArea(i.areas) : ''}
      ${part.length ? `<p class="meta">${t('participantes')} ${part.map(pessoaLink).join(', ')}</p>` : ''}
      ${i.precisa ? `<p><b>${t('precisa_de')}</b> ${esc(i.precisa)}</p>` : ''}
      <p class="meta">${prop ? t('proposta_por') + ' ' + prop + ' · ' : ''}${quando(i.data)}</p>
      ${i.status === 'ativa' ? `<div class="foot"><button class="btn sm" data-participar="${esc(i.id)}">${t('quero_participar')}</button><button class="btn sm line" data-link="i/${esc(i.id)}">${t('copiar_link')}</button></div>` : ''}
    </article>`;
  }).join('');
}
$('iniGrid').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  if (b.dataset.pessoa) return select(b.dataset.pessoa);
  if (b.dataset.link) return copiarLink(b);
  if (b.dataset.participar) dlgParticipar(D.iniciativas.find(i => i.id === b.dataset.participar));
});
$('segIni').querySelectorAll('button').forEach(b => b.onclick = () => { fIni = b.dataset.f; $('segIni').querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); renderIni(); });
['fIniArea', 'fIniConcluidas'].forEach(id => $(id).addEventListener('change', renderIni));
function dlgPropor() {
  formulario('iniciativa', t('btn_propor'), t('propor_intro'),
    `<label>${t('tipo')}</label><select name="tipo">${['Projeto', 'Encontro', 'Grupo de prática'].map(x => `<option value="${x}">${t('tipo:' + x)}</option>`).join('')}</select>
     <label>${t('titulo_l')}</label><input name="titulo" maxlength="90" required>
     <label>${t('descricao')}</label><textarea name="descricao" rows="3" maxlength="420"></textarea>
     <label>${t('areas')}${dica('ate_3')}</label>${seletorAreas(3)}
     <label>${t('quem_participa')}${dica('quem_participa_dica')}</label><input name="participantes" list="dlPessoas">
     <label>${t('precisa_l')}</label><input name="precisa" maxlength="200">
     <label>${t('seu_nome')}${dica('nome_propos_dica')}</label><input name="nome" required list="dlPessoas">${opcoesPessoas()}
     <label>${t('seu_contato')}</label><input name="contato" required>${PRIV()}
     <label class="consent"><input type="checkbox" name="consentimento" value="sim"> ${t('consent_ini')}</label>`,
    t('enviar_revisao'), t('propor_ok'),
    c => req(c, [['titulo', 'r_titulo'], ['nome', 'r_nome'], ['contato', 'r_contato']]) || (c.consentimento ? null : t('concordancia')));
  limitarAreas($('dlgBody'));
}
window.dlgPropor = dlgPropor;
$('btnPropor').onclick = dlgPropor;
function dlgParticipar(i) {
  formulario('iniciativa-participar', t('quero_participar'), t('participar_intro', esc(i.titulo)),
    `<input type="hidden" name="iniciativa_id" value="${esc(i.id)}"><input type="hidden" name="iniciativa_titulo" value="${esc(i.titulo)}">
     <label>${t('seu_nome')}</label><input name="nome" required list="dlPessoas">${opcoesPessoas()}
     <label>${t('seu_contato')}</label><input name="contato" required>
     <label>${t('contribuir')}</label><textarea name="mensagem" rows="3" maxlength="500"></textarea>${PRIV()}`,
    t('enviar'), t('participar_ok'), c => req(c, [['nome', 'r_nome'], ['contato', 'r_contato']]));
}

// ---------------------------------------------------------------- como participar
function dlgComoParticipar() {
  abrir(`<h3 id="dlgTitle">${t('btn_participar')}</h3>
    ${t('como_html')}
    <div class="row"><button class="btn" onclick="fechar()">${t('entendi')}</button></div>`);
}
$('btnParticipar').onclick = dlgComoParticipar;

// ---------------------------------------------------------------- navegação
const hint = v => ({ pessoas: t('hint_pessoas'), orgs: t('hint_orgs'), '3d': t('hint_3d') }[v] || '');
function setHash(h) { const alvo = h ? '#' + h : location.pathname + location.search; if (('#' + h) !== location.hash) history.replaceState(null, '', alvo); }
async function switchView(v) {
  view = v;
  document.querySelectorAll('.main-tabs button').forEach(x => { x.classList.toggle('on', x.dataset.v === v); x.setAttribute('aria-selected', x.dataset.v === v); });
  const board = v === 'mural' || v === 'iniciativas';
  $('main').classList.toggle('wide', board);
  $('vPessoas').hidden = v !== 'pessoas'; $('vOrgs').hidden = v !== 'orgs'; $('view3d').hidden = v !== '3d'; $('t3d').hidden = v !== '3d';
  $('vMural').hidden = v !== 'mural'; $('vIni').hidden = v !== 'iniciativas';
  $('hint').textContent = hint(v); $('hint').classList.toggle('dark', v === '3d');
  if (!board) {
    const wantsOrg = v === 'orgs' || (v === '3d' && mode3d === 'orgs');
    if (selId && wantsOrg !== selId.startsWith('o:')) closeCard();
  } else closeCard();
  if (v === 'mural') renderMural();
  if (v === 'iniciativas') renderIni();
  if (v === '3d' && !g3) await init3D();
  if (V[v] && !V[v].node) V[v].build();
  if (!selId) setHash(v === 'pessoas' ? '' : v);
  refresh();
}
function irPara(v, id) {
  const m = v === 'mural' ? D.mural.find(x => x.id === id) : D.iniciativas.find(x => x.id === id);
  if (m && m.status !== 'aberto' && m.status !== 'ativa') $(v === 'mural' ? 'fMuralAtendidos' : 'fIniConcluidas').checked = true;
  switchView(v).then(() => {
    const el = $((v === 'mural' ? 'item-' : 'ini-') + id); if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' }); el.style.outline = '3px solid var(--accent)'; setTimeout(() => el.style.outline = '', 1800);
  });
}
document.querySelectorAll('.main-tabs button').forEach(b => b.onclick = () => switchView(b.dataset.v));
$('t3d').querySelectorAll('button').forEach(b => b.onclick = () => {
  mode3d = b.dataset.m; $('t3d').querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b));
  if (selId && (mode3d === 'orgs') !== selId.startsWith('o:')) closeCard();
  if (g3) g3.graphData(graph3d()); refresh();
});
function refresh() { V.pessoas.refresh(); V.orgs.refresh(); refresh3D(); }
function rebuild() { stats(); CNT = counts(); sidebar(); for (const k in V) if (V[k].node) V[k].build(); if (g3) g3.graphData(graph3d()); if (view === 'mural') renderMural(); if (view === 'iniciativas') renderIni(); refresh(); }
window.addEventListener('resize', () => { if (g3) g3.width($('view3d').clientWidth).height($('view3d').clientHeight); });

// filtros de área do mural e das iniciativas (valor = nome em PT, texto = idioma atual)
function filtrosArea() {
  const usadas = lista => [...new Set(lista.flatMap(x => x.areas || []))].map(a => [a, nomeArea(a)]).sort((a, b) => a[1].localeCompare(b[1], window.I18N.locale()));
  for (const [id, lista] of [['fMuralArea', D.mural], ['fIniArea', D.iniciativas]]) {
    const sel = $(id), atual = sel.value;
    sel.innerHTML = `<option value="">${t('f_todas_areas')}</option>` + usadas(lista).map(([v, n]) => `<option value="${esc(v)}">${esc(n)}</option>`).join('');
    sel.value = atual;
  }
}
filtrosArea();
if (DEMO) { $('demoBanner').hidden = false; $('demoSair').href = './' + (new URLSearchParams(location.search).get('lang') ? '?lang=' + window.I18N.lang : ''); }

// idioma: botão PT | EN no cabeçalho. Troca tudo no lugar, sem recarregar e sem perder a visão aberta.
window.I18N.aplicar();
document.querySelectorAll('[data-lang]').forEach(b => b.onclick = () => window.I18N.definir(b.dataset.lang));
window.I18N.aoMudar(() => {
  nomearGrupos(); filtrosArea();
  if (dlg.open) fechar();
  rebuild();
  $('hint').textContent = hint(view);
  if (selId) select(selId);
});

// início (aceita links #mural, #iniciativas, #p/<id-da-pessoa>)
sidebar(); stats();
(function inicio() {
  const h = decodeURIComponent(location.hash.slice(1));
  if (h === 'mural' || h === 'iniciativas' || h === 'orgs' || h === '3d') return switchView(h);
  if (h === 'sobre') { switchView('pessoas'); return dlgSobre(); }
  if (h.startsWith('m/')) return irPara('mural', h.slice(2));
  if (h.startsWith('i/')) return irPara('iniciativas', h.slice(2));
  switchView('pessoas').then(() => { if (h.startsWith('p/') && byId[h.slice(2)]) setTimeout(() => select(h.slice(2), true), 300); });
})();
window.RNQ_APP = { select, switchView, get view() { return view; }, get selId() { return selId; }, setDim: d => document.querySelector(`#seg button[data-d="${d}"]`).click(),
  setLang: l => window.I18N.definir(l) };
