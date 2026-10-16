// Supabase falso para os testes e2e do painel no modo real: responde no navegador (page.route) como o Auth
// (código por e-mail, MFA), o banco (PostgREST) e a Edge Function "convidar" responderiam. Assim o teste exercita
// a biblioteca supabase-js de verdade, sem rede e sem projeto.
import fs from 'node:fs';
import path from 'node:path';

export const URL_FALSA = 'https://abcdefghijklmnopqrst.supabase.co';

export function lerDemo(raiz) {
  const js = fs.readFileSync(path.join(raiz, 'admin', 'demo-dados.js'), 'utf8');
  return JSON.parse(js.slice(js.indexOf('{'), js.lastIndexOf('}') + 1));
}

const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
function jwt(user, aal) {
  const agora = Math.floor(Date.now() / 1000);
  return `${b64({ alg: 'HS256', typ: 'JWT' })}.${b64({ sub: user.id, email: user.email, role: 'authenticated',
    aud: 'authenticated', aal, amr: [{ method: aal === 'aal2' ? 'totp' : 'otp', timestamp: agora }],
    exp: agora + 3600, iat: agora })}.assinatura`;
}

export async function supabaseFalso(page, { dados, perfil, fatorVerificado = false }) {
  const est = {
    pedidos: [], aal: null, perfil,
    user: { id: 'u-1', email: perfil ? perfil.email : 'fora@exemplo.org', aud: 'authenticated', role: 'authenticated',
            factors: fatorVerificado ? [{ id: 'f-ok', factor_type: 'totp', status: 'verified', friendly_name: 'x' }] : [] },
  };
  const sessao = () => ({ access_token: jwt(est.user, est.aal), token_type: 'bearer', expires_in: 3600,
    expires_at: Math.floor(Date.now() / 1000) + 3600, refresh_token: 'r-' + est.aal, user: est.user });
  const json = (route, status, corpo, extra = {}) => route.fulfill({ status, contentType: 'application/json',
    headers: { 'access-control-allow-origin': '*', ...extra }, body: corpo === undefined ? '' : JSON.stringify(corpo) });

  await page.route(URL_FALSA + '/**', async (route) => {
    const req = route.request();
    const u = new URL(req.url());
    const metodo = req.method();
    if (metodo === 'OPTIONS') {
      return route.fulfill({ status: 204, headers: { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*',
                                                     'access-control-allow-methods': '*' } });
    }
    let corpo = null;
    try { corpo = req.postDataJSON(); } catch (_) { corpo = req.postData(); }
    est.pedidos.push({ metodo, caminho: u.pathname, busca: u.search, corpo, auth: req.headers().authorization || '' });
    const p = u.pathname;

    // ---- Auth
    if (p === '/auth/v1/otp') return json(route, 200, {});
    if (p === '/auth/v1/verify') {
      if (corpo.token !== '123456') {
        return json(route, 403, { code: 403, error_code: 'otp_expired', msg: 'Token has expired or is invalid' });
      }
      est.aal = 'aal1';
      return json(route, 200, sessao());
    }
    if (p === '/auth/v1/user') return json(route, 200, est.user);
    if (p === '/auth/v1/logout') return json(route, 204);
    if (p === '/auth/v1/factors' && metodo === 'POST') {
      const f = { id: 'f-novo', factor_type: 'totp', status: 'unverified', friendly_name: corpo.friendly_name };
      est.user.factors.push(f);
      return json(route, 200, { id: f.id, type: 'totp', friendly_name: f.friendly_name,
        totp: { qr_code: '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40"/></svg>',
                secret: 'JBSWY3DPEHPK3PXP', uri: 'otpauth://totp/rnq' } });
    }
    let m = p.match(/^\/auth\/v1\/factors\/([^/]+)$/);
    if (m && metodo === 'DELETE') {
      est.user.factors = est.user.factors.filter(f => f.id !== m[1]);
      return json(route, 200, { id: m[1] });
    }
    m = p.match(/^\/auth\/v1\/factors\/([^/]+)\/(challenge|verify)$/);
    if (m && m[2] === 'challenge') return json(route, 200, { id: 'ch-1', type: 'totp', expires_at: Math.floor(Date.now() / 1000) + 300 });
    if (m && m[2] === 'verify') {
      if (corpo.code !== '654321') return json(route, 422, { code: 422, error_code: 'mfa_verification_failed', msg: 'Invalid TOTP code entered' });
      est.user.factors.forEach(f => { if (f.id === m[1]) f.status = 'verified'; });
      est.aal = 'aal2';
      return json(route, 200, sessao());
    }

    // ---- banco (PostgREST)
    const ok = est.perfil && (!est.perfil.mfa_exigido || est.aal === 'aal2');
    if (p.startsWith('/rest/v1/rpc/')) {
      const fn = p.split('/').pop();
      if (fn === 'rnq_meu_perfil') return json(route, 200, est.perfil ? { ...est.perfil, sessao_ok: ok } : null);
      if (!ok) return json(route, 403, { code: '42501', message: 'permission denied' });
      if (fn === 'rnq_definir_idioma') return json(route, 200, null);
      if (fn === 'rnq_painel_status') return json(route, 200, { ultima_atualizacao: dados.gerado_em,
        rotina_diaria: { ligada: false }, ultima_publicacao: { quando: dados.gerado_em, ok: false, erro: 'Testes falhando' } });
      if (fn === 'rnq_equipe_listar') return json(route, 200, dados.equipe);
      if (fn === 'rnq_decidir') {
        const i = dados.moderacao.find(x => x.id === corpo.p_id);
        Object.assign(i, { status: corpo.p_status, motivo: corpo.p_motivo, decidido_por_nome: est.perfil.nome,
                           decidido_em: new Date().toISOString(), origem_decisao: 'painel' });
        return json(route, 200, i);
      }
      if (fn === 'rnq_equipe_atualizar') return json(route, 200, { user_id: corpo.p_user, papel: corpo.p_papel, ativo: true, comunidades: corpo.p_comunidades || [] });
      return json(route, 404, { message: 'função desconhecida ' + fn });
    }
    m = p.match(/^\/rest\/v1\/(\w+)$/);
    if (m) {
      if (!ok) return json(route, 200, []);                      // RLS: sem permissão, sem linhas
      const sel = u.searchParams.get('select') || '*';
      let linhas = { comunidades: dados.comunidades.map(c => ({ ...c, ativa: true })), snapshots: dados.snapshots,
                     moderacao: dados.moderacao, auditoria: dados.auditoria }[m[1]] || [];
      const filtroEscopo = u.searchParams.get('escopo');
      if (filtroEscopo) linhas = linhas.filter(l => 'eq.' + l.escopo === filtroEscopo);
      if (sel !== '*') linhas = linhas.map(l => Object.fromEntries(sel.split(',').map(k => [k, l[k]])));
      return json(route, 200, linhas);
    }

    // ---- Edge Function
    if (p === '/functions/v1/convidar') return json(route, 200, { ok: true, novo: true, convite_enviado: true });
    return json(route, 404, { message: 'rota desconhecida ' + p });
  });
  return est;
}
