// Edge Function "receber": o Netlify avisa a cada envio de formulário do mapa, e o item aparece na hora na aba
// Moderação do painel — sem esperar o Mac. Lógica pura (sem Deno), testada no Node e comparada com o pipeline
// Python (tests/test_receber.py), para o item que chega na hora ser igual ao que a planilha gera depois.
//
// Segurança: o endereço que o Netlify chama leva uma chave secreta (?chave=...), que só o Netlify e o Supabase
// conhecem. Sem ela, nada entra. O item entra sempre pendente: nada vai para o site sem moderação.

const MAX_CORPO = 64 * 1024;

export function txt(v) { return v === null || v === undefined ? '' : String(v).trim(); }

export function chaveNome(nome) {
  return txt(nome).normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/[^\x00-\x7f]/g, '').toLowerCase()
    .replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
}
export const sim = (v) => ['sim', 's', 'yes', 'y', 'x', 'ok', 'true', '1'].includes(chaveNome(v));

export function dividirAreas(v) {
  const out = [];
  for (const parte of txt(v).split(/[;\n]/)) { const p = parte.trim(); if (p && !out.includes(p)) out.push(p); }
  return out;
}

// 'AAAA-MM-DD HH:MM' no horário de Brasília (como a planilha guarda) e o ISO correspondente.
export function brasilia(iso) {
  const d = iso ? new Date(iso) : new Date();
  const b = new Date((isNaN(d) ? Date.now() : d.getTime()) - 3 * 3600 * 1000);
  const p = (n) => String(n).padStart(2, '0');
  const texto = `${b.getUTCFullYear()}-${p(b.getUTCMonth() + 1)}-${p(b.getUTCDate())} ${p(b.getUTCHours())}:${p(b.getUTCMinutes())}`;
  return { texto, iso: texto.replace(' ', 'T') + ':00-03:00' };
}

function tituloCurto(texto, limite = 90) {           // como rnq/tecelagem.py, _titulo
  let t = txt(texto).split('\n')[0];
  for (const sep of ['. ', '; ']) if (t.includes(sep)) t = t.split(sep)[0];
  return t.length <= limite ? t : t.slice(0, limite - 1).trimEnd() + '…';
}

// Linha da planilha para um envio (rnq/tecelagem.py, adicionar_envios) + linhas do mural vindas do cadastro.
export function linhas(envio, contrato) {
  const f = contrato.formularios[envio.form];
  if (!f) return [];
  const dados = envio.dados || {};
  if (txt(dados.bot)) return [];                       // honeypot preenchido = robô
  const eid = txt(envio.id);
  if (!eid) return [];
  const quando = brasilia(envio.criado);
  const v = { ID: eid, 'Recebido em': quando.texto, ...f.padrao };
  for (const [campo, coluna] of Object.entries(f.campos)) {
    let x = dados[campo];
    if (Array.isArray(x)) x = x.map(txt).join('; ');
    v[coluna] = txt(x) || v[coluna];
  }
  if (envio.form === 'mural' && ['oferta', 'pedido'].includes(txt(v.Tipo).toLowerCase())) {
    const t = txt(v.Tipo).toLowerCase(); v.Tipo = t[0].toUpperCase() + t.slice(1);
  }
  const out = [{ aba: f.aba, linha: v, quando }];
  if (envio.form === 'participar' && ['sim', 'yes', 'true', 'on'].includes(txt(v['Mural autorizado?']).toLowerCase())) {
    const areas = txt(v.Temas).split(';').map(x => x.trim()).filter(Boolean).slice(0, 3).join('; ');
    const base = { 'Áreas': areas, Nome: v.Nome, 'Contato (privado)': v['Contato (privado)'],
      'Está no mapa como': txt(v.Visibilidade).toLowerCase() === 'mapa' ? v.Nome : null, Status: 'Aberto',
      'Recebido em': v['Recebido em'], 'Observação interna': 'Veio do cadastro "Faça parte" (aba Cadastros)' };
    const ofertas = txt(v.Ofertas), texto = txt(v['Oferta (texto)']);
    if (ofertas || texto) {
      const titulo = texto ? tituloCurto(texto) : 'Ofereço: ' + ofertas.replaceAll(';', ',');
      out.push({ aba: 'Mural', quando, linha: { ...base, ID: eid + '-oferta', Tipo: 'Oferta', 'Título': tituloCurto(titulo),
        'Descrição': [texto, texto ? ofertas : ''].filter(Boolean).join('; ') } });
    }
    if (txt(v.Pedido)) {
      out.push({ aba: 'Mural', quando, linha: { ...base, ID: eid + '-pedido', Tipo: 'Pedido',
        'Título': tituloCurto(v.Pedido), 'Descrição': txt(v.Pedido) } });
    }
  }
  return out;
}

function titulo(tipo, r) {                            // como rnq/admin.py, _titulo
  const t = {
    mural: `${txt(r.Tipo) || 'Item'}: ${txt(r['Título'])}`,
    perfil: txt(r['Pessoa no mapa']),
    ligacao: `${txt(r.Pessoa)} ↔ ${txt(r['Quem sugere'])}`,
    iniciativa: `${txt(r.Tipo) || 'Iniciativa'}: ${txt(r['Título'])}`,
    cadastro: txt(r.Nome),
    resposta: `${txt(r.Nome)} → ${txt(r.Item)}`,
    participacao: `${txt(r.Nome)} → ${txt(r.Iniciativa)}`,
  }[tipo];
  return (t.replace(/^[ :→↔]+|[ :→↔]+$/g, '') || '(sem título)').slice(0, 200);
}

// Nome de comunidade ou tema (como as pessoas escrevem) -> id da comunidade.
export function mapaComunidades(comunidades, contrato) {
  const m = new Map();
  for (const c of comunidades || []) {
    m.set(chaveNome(c.nome), c.id);
    if (c.nome_en && !m.has(chaveNome(c.nome_en))) m.set(chaveNome(c.nome_en), c.id);
  }
  for (const [k, id] of Object.entries(contrato.tema_comunidade || {})) if (!m.has(k)) m.set(k, id);
  return m;
}

// Item de moderação (mesmo formato de rnq/admin.py, itens_moderacao). Comunidades vêm das áreas citadas; as das
// pessoas o Mac acrescenta na atualização seguinte.
export function itens(envio, contrato, comunidades) {
  const porNome = mapaComunidades(comunidades, contrato);
  const areas = (v) => dividirAreas(v).map(a => porNome.get(chaveNome(a))).filter(Boolean);
  const out = [];
  for (const { aba, linha: r, quando } of linhas(envio, contrato)) {
    const tipo = contrato.formularios[envio.form] && aba === contrato.formularios[envio.form].aba
      ? contrato.formularios[envio.form].tipo : Object.keys(contrato.tipos).find(t => contrato.tipos[t].aba === aba);
    if (!tipo) continue;                                 // Saídas e Confirmações não são moderação
    const col = contrato.tipos[tipo].coluna;
    const campos = [], privado = [];
    for (const [nome, tipoCol] of contrato.colunas[aba]) {
      const v = txt(r[nome]);
      if (!v || nome === 'ID' || nome === 'Recebido em' || nome === col || contrato.no_titulo[tipo].includes(nome)) continue;
      (tipoCol === 'privado' || tipoCol === 'interno' ? privado : campos).push([nome, v]);
    }
    const alertas = [];
    if (tipo === 'cadastro') {
      if (!['mapa', ''].includes(chaveNome(r.Visibilidade))) alertas.push('fora_do_mapa');
      if (!sim(r['18 anos ou mais'])) alertas.push('sem_18');
    }
    let coms = [];
    if (tipo === 'mural' || tipo === 'iniciativa') coms = areas(r['Áreas']);
    if (tipo === 'cadastro') coms = [...areas(r.Comunidades), ...areas(r.Temas)];
    const item = {
      tipo, item_id: txt(r.ID), comunidades: [...new Set(coms)].sort(), titulo: titulo(tipo, r),
      conteudo: { aba, coluna: col, campos, alertas, bloqueio: alertas[0] || null, mapa: null },
      privado: { campos: privado }, recebido_em: quando.iso,
    };
    if (tipo === 'resposta') item.ref = txt(r['ID do item']);
    if (tipo === 'participacao') item.ref = txt(r['ID da iniciativa']);
    out.push(item);
  }
  return out;
}

function iguais(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || !a || a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

const resposta = (status, json) => ({ status, json });

// corpo: texto cru do pedido do Netlify (submission_created). Devolve {status, json}.
export async function tratarEnvio({ metodo, url, corpo, env, contrato, buscarComunidades, gravar }) {
  if (metodo !== 'POST') return resposta(405, { erro: 'Use POST' });
  const segredo = env.RNQ_RECEBER_SEGREDO || '';
  if (segredo.length < 24 || !iguais(new URL(url).searchParams.get('chave') || '', segredo)) {
    return resposta(401, { erro: 'Chave inválida' });
  }
  if (!corpo || corpo.length > MAX_CORPO) return resposta(413, { erro: 'Envio vazio ou grande demais' });
  let s;
  try { s = JSON.parse(corpo); } catch (_) { return resposta(400, { erro: 'JSON inválido' }); }
  if (env.RNQ_SITE_NOME && s.site_name && s.site_name !== env.RNQ_SITE_NOME) {
    return resposta(403, { erro: 'Site não permitido' });
  }
  const envio = { form: s.form_name, id: s.id, criado: s.created_at, dados: s.data || {} };
  if (!contrato.formularios[envio.form]) return resposta(200, { ignorado: 'formulário sem moderação' });
  const lista = itens(envio, contrato, await buscarComunidades());
  if (!lista.length) return resposta(200, { ignorado: 'nada para moderar' });
  const r = await gravar(lista);
  return resposta(200, { ok: true, novos: (r && r.novos) || 0 });
}
