// Edge Function "convidar": um admin do painel convida alguém (ou muda o acesso de quem já tem conta).
// Lógica pura, sem nada do Deno, para poder ser testada no Node (tests/sql/convidar.test.mjs).
//
// Segurança:
//  - Quem chama precisa estar logado e ser admin ATIVO com MFA (rnq_eh_admin, conferido no banco com o
//    próprio login de quem chama — não confiamos em nada que venha do navegador).
//  - Só então usamos a chave de serviço (que fica no Supabase, nunca no navegador) para convidar.
//  - Só aceita chamadas vindas do endereço do painel (CORS).

const EMAIL = /^[^\s@]{1,64}@[^\s@]{1,190}\.[^\s@]{2,}$/;

export function cabecalhosCors(origem, env) {
  const permitido = (env.RNQ_PAINEL_URL || '').replace(/\/+$/, '');
  return {
    'Access-Control-Allow-Origin': origem && origem === permitido ? origem : permitido || 'null',
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Content-Type': 'application/json; charset=utf-8',
    Vary: 'Origin',
  };
}

export function validar(corpo) {
  if (!corpo || typeof corpo !== 'object') return 'Pedido vazio';
  const email = String(corpo.email || '').trim().toLowerCase();
  if (!EMAIL.test(email) || email.length > 254) return 'E-mail inválido';
  if (!['admin', 'tecelao'].includes(corpo.papel)) return 'Papel inválido';
  const coms = corpo.comunidades ?? [];
  if (!Array.isArray(coms) || coms.length > 60 || coms.some(c => typeof c !== 'string' || !/^[a-z0-9-]{1,80}$/.test(c))) {
    return 'Comunidades inválidas';
  }
  if (corpo.papel === 'tecelao' && !coms.length) return 'Escolha ao menos uma comunidade para um tecelão';
  if (corpo.nome != null && (typeof corpo.nome !== 'string' || corpo.nome.length > 120)) return 'Nome inválido';
  if (corpo.idioma != null && !['pt', 'en'].includes(corpo.idioma)) return 'Idioma inválido';
  return null;
}

const resposta = (status, json, headers) => ({ status, headers, json });

export async function tratarConvite({ metodo, origem, autorizacao, corpo, env, criarCliente }) {
  const headers = cabecalhosCors(origem, env);
  if (metodo === 'OPTIONS') return resposta(204, undefined, headers);
  if (metodo !== 'POST') return resposta(405, { erro: 'Use POST' }, headers);
  const painel = (env.RNQ_PAINEL_URL || '').replace(/\/+$/, '');
  if (painel && origem && origem !== painel) return resposta(403, { erro: 'Origem não permitida', codigo: '42501' }, headers);
  if (!autorizacao || !/^Bearer\s+\S+/i.test(autorizacao)) {
    return resposta(401, { erro: 'Entre no painel antes de convidar', codigo: '401' }, headers);
  }

  // Chaves: as que o Supabase injeta nas Edge Functions; se as antigas estiverem desligadas no projeto,
  // valem as que o "painel_admin.py configurar" grava como segredos da função (RNQ_CHAVE_*).
  const chavePublica = env.SUPABASE_ANON_KEY || env.RNQ_CHAVE_PUBLICA;
  const chaveServico = env.SUPABASE_SERVICE_ROLE_KEY || env.RNQ_CHAVE_SECRETA;
  if (!env.SUPABASE_URL || !chavePublica || !chaveServico) {
    return resposta(500, { erro: 'Função sem configuração (rode painel_admin.py configurar)' }, headers);
  }
  const daPessoa = criarCliente(env.SUPABASE_URL, chavePublica, {
    global: { headers: { Authorization: autorizacao } }, auth: { persistSession: false } });
  const { data: usuario, error: erroUsuario } = await daPessoa.auth.getUser();
  if (erroUsuario || !usuario || !usuario.user) return resposta(401, { erro: 'Sessão inválida', codigo: '401' }, headers);
  const { data: ehAdmin, error: erroAdmin } = await daPessoa.rpc('rnq_eh_admin');
  if (erroAdmin || ehAdmin !== true) {
    return resposta(403, { erro: 'Só admin (com MFA) convida', codigo: '42501' }, headers);
  }

  const invalido = validar(corpo);
  if (invalido) return resposta(400, { erro: invalido, codigo: '22023' }, headers);
  const email = String(corpo.email).trim().toLowerCase();

  const servico = criarCliente(env.SUPABASE_URL, chaveServico, { auth: { persistSession: false } });
  const { data: existente, error: erroBusca } = await servico.rpc('rnq_usuario_por_email', { p_email: email });
  if (erroBusca) return resposta(500, { erro: erroBusca.message }, headers);
  let uid = existente;
  let conviteEnviado = false;
  if (!uid) {
    const { data, error } = await servico.auth.admin.inviteUserByEmail(email, {
      redirectTo: painel || undefined, data: { nome: corpo.nome || '' } });
    if (error) {
      const smtp = /smtp|not authorized|sending|email address/i.test(error.message || '');
      return resposta(smtp ? 502 : 500, { erro: smtp ? 'smtp: ' + error.message : error.message, codigo: smtp ? 'smtp' : '' }, headers);
    }
    uid = data.user.id;
    conviteEnviado = true;
  }
  const { data: registro, error: erroRegistro } = await servico.rpc('rnq_convite_registrar', {
    p_user: uid, p_email: email, p_nome: corpo.nome || '', p_papel: corpo.papel, p_comunidades: corpo.comunidades || [],
    p_idioma: corpo.idioma || 'pt', p_convidado_por: usuario.user.id });
  if (erroRegistro) return resposta(400, { erro: erroRegistro.message, codigo: erroRegistro.code || '' }, headers);
  return resposta(200, { ok: true, novo: !!(registro && registro.novo), convite_enviado: conviteEnviado }, headers);
}
