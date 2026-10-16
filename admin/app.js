// Painel da tecelagem — Rede Novo Quilombo (SPEC-RNQ-003).
// Sem framework: DOM direto, sempre com textContent (nada vindo dos dados vira HTML aqui).
// O único HTML gerado fora é o da "Visão da rede", que vem do pipeline e roda num iframe isolado (sandbox).
(function () {
  'use strict';

  const I18N = window.RNQ_I18N;
  const COLUNAS_EN = window.RNQ_COLUNAS_EN || {};
  const raiz = document.getElementById('app');
  const LS = {
    ler(k) { try { return localStorage.getItem('rnq-painel-' + k); } catch (_) { return null; } },
    gravar(k, v) { try { localStorage.setItem('rnq-painel-' + k, v); } catch (_) { /* sem armazenamento */ } },
  };
  const params = new URLSearchParams(location.search);

  const E = {
    api: null, idioma: 'pt', perfil: null, aba: 'visao', escopo: null,
    comunidades: [], snapshots: [], itens: [], equipe: [], auditoria: [],
    filtros: { status: 'pendente', tipo: '', comunidade: '', busca: '' },
    abertos: new Set(), recusando: null, idiomaEscolhido: false,
  };
  const T = () => I18N[E.idioma];
  window.RNQ_PAINEL = E;                 // para os testes e2e

  // ------------------------------------------------------------------ utilidades
  function h(tag, attrs, ...filhos) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else if (k === 'texto') el.textContent = v;
      else el.setAttribute(k, v === true ? '' : v);
    }
    for (const f of filhos.flat(Infinity)) {
      if (f === null || f === undefined || f === false) continue;
      el.append(f instanceof Node ? f : document.createTextNode(String(f)));
    }
    return el;
  }
  function limpar(el) { while (el.firstChild) el.removeChild(el.firstChild); }
  function anexar(el, ...filhos) {
    for (const f of filhos.flat(Infinity)) if (f !== null && f !== undefined && f !== false) el.append(f);
    return el;
  }
  function data(iso, comHora = true) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d)) return '';
    return new Intl.DateTimeFormat(T().lang, Object.assign({ day: 'numeric', month: 'short', year: 'numeric',
      timeZone: 'America/Sao_Paulo' }, comHora ? { hour: '2-digit', minute: '2-digit' } : {})).format(d);
  }
  function nomeComunidade(id) {
    const c = E.comunidades.find(x => x.id === id);
    if (!c) return id;
    return E.idioma === 'en' && c.nome_en ? c.nome_en : c.nome;
  }
  // Endereço do mapa público. Na demonstração, o mapa abre com os exemplos (?demo=1) e os itens não têm link,
  // porque a rede fictícia não está no mapa de verdade.
  function mapaUrl(trecho) {
    const cfg = window.RNQ_PAINEL_CONFIG || {};
    const base = String(cfg.mapaUrl || 'https://mapa-novoquilombo.netlify.app').replace(/\/+$/, '');
    if (E.api && E.api.modo === 'demo') return base + '/?demo=1';
    const lang = E.idioma === 'en' ? '?lang=en' : '';
    return base + '/' + lang + (trecho && /^[pmi]\/[A-Za-z0-9_.:-]+$/.test(trecho) ? '#' + trecho : '');
  }
  function rotuloColuna(c) { return E.idioma === 'en' ? (COLUNAS_EN[c] || c) : c; }
  let tempoToast;
  function toast(msg, tipo) {
    let t = document.querySelector('.toast');
    if (!t) { t = h('div', { class: 'toast', role: 'status', 'aria-live': 'polite' }); document.body.append(t); }
    t.className = 'toast' + (tipo === 'erro' ? ' erro' : '');
    t.textContent = msg;
    clearTimeout(tempoToast);
    tempoToast = setTimeout(() => t.remove(), 4200);
  }
  function erroAmigavel(e) {
    const m = String((e && e.message) || e || '').toLowerCase();
    const c = String((e && e.codigo) || '');
    if (m.includes('pelo menos um admin')) return T().erro_ultimo_admin;
    if (m.includes('não pode ser aprovado')) return T().bloqueio.fora_do_mapa;
    if (m.includes('smtp') || m.includes('not authorized') || m.includes('error sending')) return T().erro_smtp;
    if (m.includes('rate limit') || m.includes('too many') || c === '429' || m.includes('security purposes')) return T().erro_limite;
    if (m.includes('token has expired') || m.includes('otp') || m.includes('invalid totp') || m.includes('invalid code')) return T().erro_codigo;
    if (m.includes('failed to fetch') || m.includes('networkerror') || m.includes('load failed')) return T().erro_rede;
    if (c === '42501' || m.includes('permiss') || m.includes('só admin')) return T().erro_permissao;
    return T().erro_generico;
  }
  function carregarScript(src) {
    return new Promise((ok, falha) => {
      const s = document.createElement('script');
      s.src = src; s.onload = ok; s.onerror = () => falha(new Error('script ' + src));
      document.head.append(s);
    });
  }
  function aplicarIdioma() {
    document.documentElement.lang = T().lang;
    document.title = `${T().titulo} · ${T().rede}`;
  }
  async function trocarIdioma() {
    E.idioma = E.idioma === 'pt' ? 'en' : 'pt';
    E.idiomaEscolhido = true;
    LS.gravar('idioma', E.idioma);
    aplicarIdioma();
    if (E.perfil) { E.api.definirIdioma(E.idioma).catch(() => {}); desenharApp(); } else telaAtual();
  }
  function botaoIdioma(classe) {
    return h('button', { type: 'button', class: classe || 'btn link', lang: E.idioma === 'pt' ? 'en' : 'pt',
                         onclick: trocarIdioma, 'data-teste': 'idioma' }, T().outra_lingua);
  }

  // ------------------------------------------------------------------ entrada (login e MFA)
  function flor() {
    // Flor da Vida: 19 círculos numa grade hexagonal, dentro de uma moldura. Desenhada uma vez, ao abrir.
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', '-34 -34 68 68');
    svg.setAttribute('aria-hidden', 'true');
    const r = 10, pts = [[0, 0]];
    for (let anel = 1; anel <= 2; anel++) {
      for (let i = 0; i < 6; i++) {
        const a = Math.PI / 3 * i, b = Math.PI / 3 * (i + 2);
        for (let j = 0; j < anel; j++) {
          pts.push([r * (anel * Math.cos(a) + j * Math.cos(b)), r * (anel * Math.sin(a) + j * Math.sin(b))]);
        }
      }
    }
    pts.forEach(([x, y], i) => {
      const c = document.createElementNS(ns, 'circle');
      c.setAttribute('cx', x.toFixed(3)); c.setAttribute('cy', y.toFixed(3)); c.setAttribute('r', r);
      c.setAttribute('pathLength', '64');
      c.style.animationDelay = (i * 0.07).toFixed(2) + 's';
      svg.append(c);
    });
    const m = document.createElementNS(ns, 'circle');
    m.setAttribute('r', 30); m.setAttribute('class', 'moldura'); m.setAttribute('pathLength', '64');
    svg.append(m);
    return svg;
  }
  function moldura(...conteudo) {
    limpar(raiz);
    raiz.append(h('div', { class: 'entrada' },
      h('div', { class: 'flor' }, flor()),
      h('div', { class: 'lado' }, h('div', { class: 'cartao' },
        h('div', { class: 'marca' }, h('img', { src: 'img/olho-horus.png', alt: '' }), h('span', {}, T().rede)),
        ...conteudo,
        h('p', { class: 'suave pequeno', style: 'margin-top:28px' }, botaoIdioma())))));
  }
  let telaAtual = () => {};
  function mensagem(el, texto, tipo) {
    el.className = 'msg ' + (tipo || 'info'); el.textContent = texto; el.classList.remove('oculto');
  }

  function telaEntrar(emailInicial) {
    telaAtual = () => telaEntrar(emailInicial);
    const msg = h('div', { class: 'msg oculto', role: 'alert' });
    const email = h('input', { type: 'email', id: 'email', autocomplete: 'email', required: true, value: emailInicial || '' });
    const botao = h('button', { class: 'btn', type: 'submit' }, T().enviar_codigo);
    moldura(
      h('h1', {}, T().entrar_titulo), h('p', {}, T().entrar_sub),
      h('form', { onsubmit: async (ev) => {
        ev.preventDefault();
        const v = email.value.trim().toLowerCase();
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return mensagem(msg, T().erro_email, 'erro');
        botao.disabled = true; botao.textContent = T().enviando;
        try { await E.api.enviarCodigo(v); telaCodigo(v); }
        catch (e) { botao.disabled = false; botao.textContent = T().enviar_codigo; mensagem(msg, erroAmigavel(e), 'erro'); }
      } }, h('label', { class: 'campo', for: 'email' }, T().email), email,
         h('div', { class: 'acoes' }, botao), msg),
      h('p', { class: 'suave pequeno', style: 'margin-top:18px' }, T().so_convite));
    email.focus();
  }

  function telaCodigo(email) {
    telaAtual = () => telaCodigo(email);
    const msg = h('div', { class: 'msg info', role: 'status' }, T().codigo_enviado(email));
    const cod = h('input', { type: 'text', id: 'codigo', class: 'codigo', inputmode: 'numeric', autocomplete: 'one-time-code',
                             maxlength: '6', pattern: '[0-9]{6}', required: true });
    const botao = h('button', { class: 'btn', type: 'submit' }, T().entrar);
    moldura(
      h('h1', {}, T().entrar_titulo),
      msg,
      h('form', { onsubmit: async (ev) => {
        ev.preventDefault();
        botao.disabled = true;
        try { await E.api.verificarCodigo(email, cod.value.replace(/\D/g, '')); await posLogin(); }
        catch (e) { botao.disabled = false; mensagem(msg, erroAmigavel(e), 'erro'); cod.select(); }
      } }, h('label', { class: 'campo', for: 'codigo' }, T().codigo), cod,
         h('div', { class: 'acoes' }, botao,
           h('button', { type: 'button', class: 'btn claro', onclick: async () => {
             try { await E.api.enviarCodigo(email); mensagem(msg, T().codigo_enviado(email)); }
             catch (e) { mensagem(msg, erroAmigavel(e), 'erro'); }
           } }, T().reenviar),
           h('button', { type: 'button', class: 'btn link', onclick: () => telaEntrar(email) }, T().trocar_email))));
    cod.focus();
  }

  function telaMfa(estado) {
    telaAtual = () => telaMfa(estado);
    const msg = h('div', { class: 'msg oculto', role: 'alert' });
    const cod = h('input', { type: 'text', id: 'mfa', class: 'codigo', inputmode: 'numeric', autocomplete: 'one-time-code',
                             maxlength: '6', required: true });
    const botao = h('button', { class: 'btn', type: 'submit' }, T().confirmar);
    const form = h('form', { onsubmit: async (ev) => {
      ev.preventDefault();
      botao.disabled = true;
      try { await E.api.mfaVerificar(estado.fatorId, cod.value.replace(/\D/g, '')); await posLogin(); }
      catch (e) { botao.disabled = false; mensagem(msg, erroAmigavel(e), 'erro'); cod.select(); }
    } }, h('label', { class: 'campo', for: 'mfa' }, T().codigo), cod,
       h('div', { class: 'acoes' }, botao, h('button', { type: 'button', class: 'btn link', onclick: sair }, T().sair)), msg);
    if (estado.cadastro) {
      moldura(h('h1', {}, T().mfa_cadastro_titulo), h('p', {}, T().mfa_cadastro_sub),
        estado.qr ? h('div', { class: 'qr' }, h('img', { src: estado.qr, alt: 'QR code' })) : null,
        h('p', { class: 'pequeno suave' }, T().mfa_segredo), h('p', { class: 'segredo' }, estado.segredo), form);
    } else {
      moldura(h('h1', {}, T().mfa_titulo), h('p', {}, T().mfa_sub), form);
    }
    cod.focus();
  }

  function telaSemAcesso(email) {
    telaAtual = () => telaSemAcesso(email);
    moldura(h('h1', {}, T().sem_acesso_titulo), h('p', {}, T().sem_acesso_sub),
      email ? h('p', { class: 'segredo' }, email) : null,
      h('div', { class: 'acoes' }, h('button', { class: 'btn claro', onclick: sair }, T().sair)));
  }

  async function sair() {
    try { await E.api.sair(); } catch (_) { /* já saiu */ }
    E.perfil = null;
    telaEntrar();
  }

  async function posLogin() {
    const perfil = await E.api.perfil();
    const sessao = await E.api.sessao();
    if (!perfil) return telaSemAcesso(sessao && sessao.user && sessao.user.email);
    if (perfil.mfa_exigido) {
      const st = await E.api.mfa();
      if (st.atual !== 'aal2') {
        if (st.verificado) return telaMfa({ fatorId: st.verificado.id });
        const novo = await E.api.mfaCadastrar();
        return telaMfa({ cadastro: true, fatorId: novo.id, qr: novo.qr, segredo: novo.segredo });
      }
    }
    E.perfil = perfil;
    if (!E.idiomaEscolhido && perfil.idioma) { E.idioma = perfil.idioma; aplicarIdioma(); }
    await carregarTudo();
    desenharApp();
  }

  // ------------------------------------------------------------------ dados
  async function carregarTudo() {
    const admin = E.perfil.papel === 'admin';
    const [coms, snaps, itens, equipe, aud] = await Promise.all([
      E.api.comunidades(), E.api.snapshots(), E.api.moderacao(),
      admin ? E.api.equipe() : Promise.resolve([]), admin ? E.api.auditoria() : Promise.resolve([])]);
    E.comunidades = coms || []; E.snapshots = snaps || []; E.itens = itens || [];
    E.equipe = equipe || []; E.auditoria = aud || [];
    const escopos = E.snapshots.map(s => s.escopo);
    if (!escopos.includes(E.escopo)) E.escopo = escopos.includes('rede') ? 'rede' : (escopos[0] || null);
    if (!admin && ['equipe', 'historico'].includes(E.aba)) E.aba = 'visao';
  }

  // ------------------------------------------------------------------ app
  function desenharApp() {
    telaAtual = desenharApp;
    const t = T();
    const admin = E.perfil.papel === 'admin';
    const pendentes = E.itens.filter(i => i.status === 'pendente').length;
    const abas = [['visao', t.aba_visao], ['moderacao', t.aba_moderacao, pendentes]];
    if (admin) abas.push(['equipe', t.aba_equipe], ['historico', t.aba_historico]);
    limpar(raiz);
    if (E.api.modo === 'demo') raiz.append(faixaDemo());
    const nav = h('nav', { class: 'abas', role: 'tablist', 'aria-label': t.titulo },
      abas.map(([id, nome, n]) => h('button', {
        role: 'tab', id: 'aba-' + id, 'aria-selected': String(E.aba === id), 'aria-controls': 'conteudo',
        tabindex: E.aba === id ? '0' : '-1', 'data-aba': id,
        onclick: () => { E.aba = id; desenharApp(); document.getElementById('aba-' + id).focus(); },
        onkeydown: (ev) => {
          const i = abas.findIndex(a => a[0] === id);
          const prox = ev.key === 'ArrowRight' ? abas[(i + 1) % abas.length] : ev.key === 'ArrowLeft' ? abas[(i - 1 + abas.length) % abas.length] : null;
          if (prox) { ev.preventDefault(); E.aba = prox[0]; desenharApp(); document.getElementById('aba-' + prox[0]).focus(); }
        } }, nome, n ? h('span', { class: 'contador', 'aria-label': `${n}` }, String(n)) : null)));
    raiz.append(h('header', { class: 'lintel' },
      h('div', { class: 'topo' },
        h('img', { src: 'img/olho-horus.png', alt: '' }),
        h('div', {}, h('h1', {}, t.titulo), h('div', { class: 'rede' }, t.rede)),
        h('div', { class: 'eu' },
          h('span', { 'data-teste': 'quem' }, E.perfil.nome || E.perfil.email),
          h('span', { class: 'papel' }, admin ? t.papel_admin : t.papel_tecelao),
          h('a', { class: 'mapa', href: mapaUrl(), target: '_blank', rel: 'noopener noreferrer', title: t.nota_mapa,
                   'data-teste': 'ver-mapa' }, t.ver_mapa),
          h('button', { type: 'button', onclick: trocarIdioma, lang: E.idioma === 'pt' ? 'en' : 'pt', 'data-teste': 'idioma' }, t.outra_lingua),
          h('button', { type: 'button', onclick: sair }, t.sair))),
      nav));
    const main = h('main', { class: 'conteudo', id: 'conteudo', role: 'tabpanel', 'aria-labelledby': 'aba-' + E.aba });
    raiz.append(main);
    ({ visao: desenharVisao, moderacao: desenharModeracao, equipe: desenharEquipe, historico: desenharHistorico })[E.aba](main);
  }

  function faixaDemo() {
    const sel = h('select', { 'aria-label': T().demo_ver_como, 'data-teste': 'ver-como', onchange: async (ev) => {
      E.api.verComo(ev.target.value);
      E.perfil = await E.api.perfil();
      await carregarTudo();
      desenharApp();
    } }, E.api.pessoas().map(p => h('option', { value: p.user_id, selected: p.user_id === E.perfil.user_id },
      `${p.nome} · ${p.papel === 'admin' ? T().papel_admin : T().papel_tecelao}` +
      (p.comunidades.length ? ` (${p.comunidades.map(nomeComunidade).join(', ')})` : ''))));
    return h('div', { class: 'demo-faixa', role: 'note' }, h('span', {}, T().demo_faixa),
      h('label', {}, T().demo_ver_como + ' ', sel));
  }

  // ---- visão da rede
  function desenharVisao(main) {
    const t = T();
    if (!E.snapshots.length) {
      const semComunidade = E.perfil.papel !== 'admin' && !(E.perfil.comunidades || []).length;
      main.append(h('div', { class: 'vazio' },
        h('h3', {}, semComunidade ? t.sem_comunidade_titulo : t.aba_visao),
        h('p', {}, semComunidade ? t.sem_comunidade_sub : t.sem_snapshot)));
      return;
    }
    const snap = E.snapshots.find(s => s.escopo === E.escopo) || E.snapshots[0];
    const ordem = E.snapshots.slice().sort((a, b) => (a.escopo === 'rede' ? -1 : b.escopo === 'rede' ? 1 :
      nomeEscopo(a).localeCompare(nomeEscopo(b), t.lang)));
    main.append(h('div', { class: 'cabeca' },
      h('div', {}, h('h2', {}, nomeEscopo(snap)), h('p', {}, t.atualizado(data(snap.gerado_em))))));
    if (ordem.length > 1) {
      main.append(h('div', { class: 'escopos', role: 'group', 'aria-label': t.escopo },
        ordem.map(s => h('button', { type: 'button', class: 'escopo', 'aria-pressed': String(s.escopo === snap.escopo),
          'data-escopo': s.escopo, onclick: () => { E.escopo = s.escopo; desenharApp(); } }, nomeEscopo(s)))));
    }
    const r = snap.resumo || {};
    main.append(h('div', { class: 'resumo' },
      h('div', {}, h('b', {}, String(r.pessoas ?? '–')), h('span', {}, t.r_pessoas)),
      h('div', {}, h('b', {}, r.pct_conectadas != null ? Math.round(r.pct_conectadas * 100) + '%' : '–'), h('span', {}, t.r_conectadas)),
      h('div', {}, h('b', { style: 'font-size:20px' }, (r.fase_nome && r.fase_nome[E.idioma]) || '–')),
      h('div', { class: 'espera' }, h('b', {}, String(r.pendentes ?? 0)), h('span', {}, t.r_pendentes)),
      h('div', {}, h('b', {}, String(r.sugestoes ?? 0)), h('span', {}, t.r_sugestoes))));
    const iframe = h('iframe', { class: 'visao', title: nomeEscopo(snap), sandbox: 'allow-scripts', 'data-teste': 'visao',
                                 referrerpolicy: 'no-referrer', loading: 'eager' });
    main.append(iframe);
    E.api.snapshotHtml(snap.escopo, E.idioma).then(html => {
      iframe.srcdoc = html || `<p style="font-family:sans-serif;padding:20px">${t.sem_snapshot.replace(/[<>&]/g, '')}</p>`;
    }).catch(e => toast(erroAmigavel(e), 'erro'));
  }
  function nomeEscopo(s) {
    if (s.escopo === 'rede') return T().escopo_rede;
    return (s.resumo && s.resumo.nome && s.resumo.nome[E.idioma]) || nomeComunidade(s.escopo);
  }
  // Mensagens do iframe isolado: só altura e "copiar". Conferimos que vieram do nosso iframe.
  window.addEventListener('message', (ev) => {
    const frame = document.querySelector('iframe.visao');
    if (!frame || ev.source !== frame.contentWindow || !ev.data || typeof ev.data !== 'object') return;
    if (typeof ev.data.rnqAltura === 'number') frame.style.height = Math.min(Math.max(ev.data.rnqAltura + 4, 400), 40000) + 'px';
    if (typeof ev.data.rnqCopiar === 'string') {
      const texto = ev.data.rnqCopiar.slice(0, 20000);
      (navigator.clipboard ? navigator.clipboard.writeText(texto) : Promise.reject())
        .then(() => toast(T().copiado_aviso)).catch(() => {
          const ta = h('textarea', { style: 'position:fixed;opacity:0' }); ta.value = texto; document.body.append(ta);
          ta.select(); try { document.execCommand('copy'); toast(T().copiado_aviso); } catch (_) { /* sem cópia */ }
          ta.remove();
        });
    }
  });

  // ---- moderação
  const TAREFA = new Set(['resposta', 'participacao']);
  function rotuloStatus(i) {
    const t = T();
    if (TAREFA.has(i.tipo)) return i.status === 'aprovado' ? t.st1_feito : i.status === 'recusado' ? t.st1_nao_vai : t.st1_pendente;
    return t['st1_' + i.status];
  }
  function filtrar() {
    const f = E.filtros, q = f.busca.trim().toLowerCase();
    return E.itens.filter(i => (!f.status || i.status === f.status) && (!f.tipo || i.tipo === f.tipo) &&
      (!f.comunidade || (f.comunidade === '_sem' ? !i.comunidades.length : i.comunidades.includes(f.comunidade))) &&
      (!q || JSON.stringify([i.titulo, i.conteudo, i.privado]).toLowerCase().includes(q)));
  }
  function desenharModeracao(main) {
    const t = T();
    const contagem = (st) => E.itens.filter(i => !st || i.status === st).length;
    const seg = h('div', { class: 'segmento' }, [['pendente', t.st_pendente], ['aprovado', t.st_aprovado],
      ['recusado', t.st_recusado], ['', t.todos]].map(([st, nome]) => h('button', {
        type: 'button', 'aria-pressed': String(E.filtros.status === st), 'data-status': st || 'todos',
        onclick: () => { E.filtros.status = st; desenharApp(); } }, h('span', {}, nome), h('span', { class: 'suave' }, String(contagem(st))))));
    const tipos = Object.keys(t.tipos).filter(k => E.itens.some(i => i.tipo === k));
    const comsUsadas = [...new Set(E.itens.flatMap(i => i.comunidades))].sort((a, b) => nomeComunidade(a).localeCompare(nomeComunidade(b)));
    const selTipo = h('select', { id: 'f-tipo', onchange: (ev) => { E.filtros.tipo = ev.target.value; desenharApp(); } },
      h('option', { value: '' }, t.todos), tipos.map(k => h('option', { value: k, selected: E.filtros.tipo === k }, t.tipos[k])));
    const selCom = h('select', { id: 'f-com', onchange: (ev) => { E.filtros.comunidade = ev.target.value; desenharApp(); } },
      h('option', { value: '' }, t.todas), comsUsadas.map(c => h('option', { value: c, selected: E.filtros.comunidade === c }, nomeComunidade(c))),
      E.perfil.papel === 'admin' && E.itens.some(i => !i.comunidades.length)
        ? h('option', { value: '_sem', selected: E.filtros.comunidade === '_sem' }, t.sem_comunidade_item) : null);
    const busca = h('input', { type: 'search', id: 'f-busca', value: E.filtros.busca, oninput: (ev) => {
      E.filtros.busca = ev.target.value; desenharLista(lista); } });
    const lista = h('div', { class: 'lista', 'aria-live': 'polite' });
    main.append(h('div', { class: 'cabeca' }, h('div', {}, h('h2', {}, t.aba_moderacao))),
      h('div', { class: 'mod' },
        h('aside', { class: 'filtros' },
          h('fieldset', { class: 'status' }, h('legend', {}, t.filtro_status), seg),
          h('fieldset', {}, h('legend', {}, h('label', { for: 'f-tipo' }, t.filtro_tipo)), selTipo),
          h('fieldset', {}, h('legend', {}, h('label', { for: 'f-com' }, t.filtro_comunidade)), selCom),
          h('fieldset', { class: 'busca' }, h('legend', {}, h('label', { for: 'f-busca' }, t.filtro_busca)), busca)),
        h('section', {}, h('p', { class: 'aviso-vale' }, t.vale_quando), lista)));
    desenharLista(lista);
  }
  function desenharLista(lista) {
    const t = T();
    limpar(lista);
    const itens = filtrar();
    if (!itens.length) {
      lista.append(h('div', { class: 'vazio' }, h('p', {}, E.itens.length ? t.nenhum_resultado : t.nenhum_item)));
      return;
    }
    itens.forEach(i => lista.append(cartaoItem(i)));
  }
  function cartaoItem(i) {
    const t = T();
    const tarefa = TAREFA.has(i.tipo);
    const bloqueio = i.conteudo && i.conteudo.bloqueio;
    const art = h('article', { class: 'item', 'data-status': i.status, 'data-id': String(i.id), 'data-tipo': i.tipo });
    const campos = (i.conteudo && i.conteudo.campos) || [];
    const privados = (i.privado && i.privado.campos) || [];
    const aberto = E.abertos.has(i.id);
    anexar(art,
      h('div', { class: 'linha1' },
        h('span', { class: 'tipo', title: t.tipos_ajuda[i.tipo] || '' }, t.tipos[i.tipo] || i.tipo),
        h('h3', {}, i.titulo),
        h('span', { class: 'estado ' + i.status }, rotuloStatus(i))),
      h('div', { class: 'meta' },
        i.recebido_em ? h('span', {}, t.recebido(data(i.recebido_em, false))) : null,
        i.comunidades.length ? h('span', { class: 'chips' }, i.comunidades.map(c => h('span', { class: 'chip' }, nomeComunidade(c))))
          : h('span', {}, t.sem_comunidade_item)),
      campos.length ? h('dl', { class: 'campos' }, campos.map(([k, v]) => [h('dt', {}, rotuloColuna(k)), h('dd', {}, v)])) : null,
      bloqueio ? h('div', { class: 'alerta', role: 'note' }, t.bloqueio[bloqueio] || bloqueio) : null);
    if (privados.length) {
      anexar(art, h('button', { type: 'button', class: 'btn link', 'aria-expanded': String(aberto), 'data-teste': 'privado',
        onclick: () => { aberto ? E.abertos.delete(i.id) : E.abertos.add(i.id); art.replaceWith(cartaoItem(i)); } },
        aberto ? t.esconder_privado : t.mostrar_privado));
      if (aberto) {
        art.append(h('div', { class: 'privado' }, h('h4', {}, t.privado_titulo),
          h('dl', { class: 'campos' }, privados.map(([k, v]) => [h('dt', {}, rotuloColuna(k)), h('dd', {}, v)]))));
      }
    }
    if (i.status !== 'pendente') {
      const quem = i.origem_decisao === 'planilha' ? t.pela_planilha : t.decidido(rotuloStatus(i), i.decidido_por_nome, data(i.decidido_em));
      art.append(h('p', { class: 'decidido' }, quem, i.motivo ? ` — "${i.motivo}"` : ''));
    }
    const botoes = h('div', { class: 'botoes' });
    if (E.recusando === i.id) {
      const motivo = h('textarea', { id: 'motivo-' + i.id, maxlength: '500' });
      art.append(h('div', { class: 'recusa' }, h('label', { class: 'campo', for: 'motivo-' + i.id }, t.motivo), motivo,
        h('div', { class: 'botoes' },
          h('button', { type: 'button', class: 'btn recusar', 'data-acao': 'confirmar-recusa',
                        onclick: () => decidir(i, 'recusado', motivo.value) }, t.confirmar_recusa),
          h('button', { type: 'button', class: 'btn claro', onclick: () => { E.recusando = null; art.replaceWith(cartaoItem(i)); } }, t.cancelar))));
      setTimeout(() => motivo.focus(), 0);
    } else if (i.status === 'pendente') {
      botoes.append(
        h('button', { type: 'button', class: 'btn aprovar', disabled: !!bloqueio, 'data-acao': 'aprovar',
                      onclick: () => decidir(i, 'aprovado') }, tarefa ? t.marcar_feito : t.aprovar),
        h('button', { type: 'button', class: 'btn recusar', 'data-acao': 'recusar',
                      onclick: () => { E.recusando = i.id; art.replaceWith(cartaoItem(i)); } }, tarefa ? t.nao_vai : t.recusar));
    } else {
      botoes.append(h('button', { type: 'button', class: 'btn claro', 'data-acao': 'desfazer',
                                  onclick: () => decidir(i, 'pendente') }, t.desfazer));
    }
    const alvo = i.conteudo && i.conteudo.mapa;
    if (alvo && E.api.modo !== 'demo' && E.recusando !== i.id) {
      botoes.append(h('a', { class: 'btn link', href: mapaUrl(alvo), target: '_blank', rel: 'noopener noreferrer',
                             title: t.nota_mapa, 'data-acao': 'ver-no-mapa' }, t.ver_no_mapa));
    }
    art.append(botoes);
    return art;
  }
  async function decidir(item, status, motivo) {
    try {
      const novo = await E.api.decidir(item.id, status, motivo);
      Object.assign(item, novo);
      E.recusando = null;
      toast(T().feito_ok[status]);
      if (E.perfil.papel === 'admin') E.api.auditoria().then(a => { E.auditoria = a; }).catch(() => {});
      desenharApp();
    } catch (e) { toast(erroAmigavel(e), 'erro'); }
  }

  // ---- equipe
  function marcasComunidades(nome, selecionadas) {
    return h('div', { class: 'marcas', role: 'group' }, E.comunidades.filter(c => c.ativa !== false).map(c =>
      h('label', {}, h('input', { type: 'checkbox', name: nome, value: c.id, checked: selecionadas.includes(c.id) }), nomeComunidade(c.id))));
  }
  function lerMarcas(el) { return [...el.querySelectorAll('input[type=checkbox]:checked')].map(x => x.value); }

  function desenharEquipe(main) {
    const t = T();
    main.append(h('div', { class: 'cabeca' }, h('div', {}, h('h2', {}, t.aba_equipe), h('p', {}, t.equipe_sub))));
    const lista = h('div', {});
    E.equipe.forEach(p => lista.append(cartaoPessoa(p)));
    main.append(h('div', { class: 'equipe' }, h('section', {}, lista), formularioConvite()));
  }
  function cartaoPessoa(p) {
    const t = T();
    const eu = p.user_id === E.perfil.user_id;
    const papel = h('select', { 'aria-label': t.papel, 'data-campo': 'papel' },
      h('option', { value: 'tecelao', selected: p.papel === 'tecelao' }, t.papel_tecelao),
      h('option', { value: 'admin', selected: p.papel === 'admin' }, t.papel_admin));
    const coms = marcasComunidades('c-' + p.user_id, p.comunidades || []);
    const todaRede = h('p', { class: 'suave' }, t.ve_rede_toda);
    const ajustar = () => { coms.classList.toggle('oculto', papel.value === 'admin'); todaRede.classList.toggle('oculto', papel.value !== 'admin'); };
    papel.addEventListener('change', ajustar);
    ajustar();
    const msg = h('span', { class: 'suave pequeno', role: 'status' });
    const salvar = h('button', { type: 'button', class: 'btn', 'data-acao': 'salvar', onclick: async () => {
      const comunidades = lerMarcas(coms);
      if (papel.value === 'tecelao' && !comunidades.length) return toast(t.escolha_comunidade, 'erro');
      try {
        const r = await E.api.atualizarMembro(p.user_id, { papel: papel.value, comunidades: papel.value === 'admin' ? [] : comunidades });
        Object.assign(p, r);
        msg.textContent = t.salvo;
        await recarregarEquipe(eu);
      } catch (e) { toast(erroAmigavel(e), 'erro'); }
    } }, t.salvar);
    const acesso = h('button', { type: 'button', class: p.ativo ? 'btn recusar' : 'btn claro', 'data-acao': 'acesso',
      onclick: async () => {
        if (p.ativo && !window.confirm(t.confirmar_desativar(p.nome || p.email))) return;
        try { await E.api.atualizarMembro(p.user_id, { ativo: !p.ativo }); await recarregarEquipe(eu); }
        catch (e) { toast(erroAmigavel(e), 'erro'); }
      } }, p.ativo ? t.desativar : t.reativar);
    return h('article', { class: 'pessoa', 'data-ativo': String(p.ativo), 'data-email': p.email },
      h('div', { class: 'linha1' }, h('h3', {}, p.nome || p.email, eu ? ` (${t.voce})` : ''),
        h('span', { class: 'estado ' + (p.ativo ? 'aprovado' : 'recusado') }, p.ativo ? t.ativo : t.inativo)),
      h('div', { class: 'meta' }, h('span', {}, p.email), h('span', {}, p.mfa ? t.mfa_sim : t.mfa_nao),
        h('span', {}, p.ultimo_acesso ? t.ultimo_acesso(data(p.ultimo_acesso)) : t.nunca_entrou)),
      h('div', { class: 'grade' }, h('div', {}, h('label', { class: 'campo' }, t.papel), papel),
        h('div', {}, h('label', { class: 'campo' }, t.comunidades), coms, todaRede)),
      h('div', { class: 'botoes' }, salvar, acesso, msg));
  }
  async function recarregarEquipe(mudeiEu) {
    if (mudeiEu) { E.perfil = await E.api.perfil(); if (!E.perfil) return sair(); if (E.perfil.papel !== 'admin') E.aba = 'visao'; }
    await carregarTudo();
    desenharApp();
  }
  function formularioConvite() {
    const t = T();
    const email = h('input', { type: 'email', id: 'c-email', required: true, autocomplete: 'off' });
    const nome = h('input', { type: 'text', id: 'c-nome', autocomplete: 'off' });
    const papel = h('select', { id: 'c-papel' }, h('option', { value: 'tecelao' }, t.papel_tecelao), h('option', { value: 'admin' }, t.papel_admin));
    const idioma = h('select', { id: 'c-idioma' }, h('option', { value: 'pt', selected: E.idioma === 'pt' }, 'Português'),
      h('option', { value: 'en', selected: E.idioma === 'en' }, 'English'));
    const coms = marcasComunidades('convite', []);
    const blocoComs = h('div', {}, h('label', { class: 'campo' }, t.comunidades), coms);
    papel.addEventListener('change', () => blocoComs.classList.toggle('oculto', papel.value === 'admin'));
    const msg = h('div', { class: 'msg oculto', role: 'status' });
    const botao = h('button', { class: 'btn', type: 'submit' }, t.convidar);
    return h('aside', { class: 'painel-lateral' }, h('h3', {}, t.convidar_titulo),
      h('form', { 'data-teste': 'convite', onsubmit: async (ev) => {
        ev.preventDefault();
        const v = email.value.trim().toLowerCase();
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) return mensagem(msg, t.erro_email, 'erro');
        const comunidades = lerMarcas(coms);
        if (papel.value === 'tecelao' && !comunidades.length) return mensagem(msg, t.escolha_comunidade, 'erro');
        botao.disabled = true;
        try {
          const r = await E.api.convidar({ email: v, nome: nome.value.trim(), papel: papel.value,
                                           comunidades: papel.value === 'admin' ? [] : comunidades, idioma: idioma.value });
          await carregarTudo();
          desenharApp();
          toast(t.convite_ok(v, r && r.novo));
        } catch (e) { botao.disabled = false; mensagem(msg, erroAmigavel(e), 'erro'); }
      } },
      h('label', { class: 'campo', for: 'c-email' }, t.email), email,
      h('label', { class: 'campo', for: 'c-nome' }, t.nome), nome,
      h('label', { class: 'campo', for: 'c-papel' }, t.papel), papel,
      blocoComs,
      h('label', { class: 'campo', for: 'c-idioma' }, t.idioma), idioma,
      h('div', { class: 'botoes' }, botao), msg),
      h('p', { class: 'suave pequeno', style: 'margin-top:14px' }, t.smtp_aviso));
  }

  // ---- histórico
  function desenharHistorico(main) {
    const t = T();
    main.append(h('div', { class: 'cabeca' }, h('div', {}, h('h2', {}, t.aba_historico), h('p', {}, t.historico_sub))));
    if (!E.auditoria.length) { main.append(h('div', { class: 'vazio' }, h('p', {}, t.nada_historico))); return; }
    main.append(h('ol', { class: 'historico' }, E.auditoria.map(a => {
      const d = a.detalhes || {};
      const acao = t.acoes[a.acao] || a.acao;
      let texto;
      if (a.acao === 'pipeline.sincronizar') texto = [h('b', {}, acao), ' — ', t.pipeline_detalhe(d)];
      else if (a.acao === 'moderacao.decidir') {
        const tipo = String(a.alvo || '').split(':')[0];
        const st = TAREFA.has(tipo) ? rotuloStatus({ tipo, status: d.para }) : t['st1_' + d.para] || d.para;
        texto = [h('b', {}, a.quem_email || t.sistema), ` ${acao}: `, `"${d.titulo || a.alvo}"`, ` → ${st}`, d.motivo ? ` ("${d.motivo}")` : ''];
      } else texto = [h('b', {}, a.quem_email || t.sistema), ` ${acao} `, a.alvo || ''];
      return h('li', { class: a.acao === 'pipeline.sincronizar' ? 'pipeline' : '' }, h('time', { datetime: a.quando }, data(a.quando)), h('div', {}, texto));
    })));
  }

  // ------------------------------------------------------------------ início
  async function iniciar() {
    const salvo = LS.ler('idioma');
    E.idioma = salvo || ((navigator.language || 'pt').toLowerCase().startsWith('pt') ? 'pt' : 'en');
    E.idiomaEscolhido = !!salvo;
    if (params.get('lang') === 'en' || params.get('lang') === 'pt') { E.idioma = params.get('lang'); E.idiomaEscolhido = true; }
    aplicarIdioma();
    raiz.textContent = T().carregando;
    const cfg = window.RNQ_PAINEL_CONFIG;
    const demo = params.has('demo') || !cfg || !cfg.supabaseUrl;
    try {
      if (demo) {
        await carregarScript('demo-dados.js');
        await carregarScript('demo.js');
        E.api = new window.RNQ_API.ApiDemo(window.RNQ_DEMO);
        return await posLogin();
      }
      await carregarScript('vendor/supabase.js');
      E.api = new window.RNQ_API.ApiSupabase(cfg);
      E.api.aoMudarSessao((evento) => { if (evento === 'SIGNED_OUT' && E.perfil) { E.perfil = null; telaEntrar(); } });
      const sessao = await E.api.sessao();
      if (sessao) await posLogin(); else telaEntrar();
    } catch (e) {
      console.error(e);
      limpar(raiz);
      raiz.append(h('div', { class: 'carregando', role: 'alert' }, erroAmigavel(e)));
    }
    window.RNQ_PRONTO = true;
  }
  iniciar().then(() => { window.RNQ_PRONTO = true; });
})();
