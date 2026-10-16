// Edge Function "receber" (Supabase): o Netlify chama a cada envio de formulário do mapa. Publicada por
// "python3 painel_admin.py configurar", sem exigir login (verify_jwt = false): quem protege é a chave na URL.
import { createClient } from 'npm:@supabase/supabase-js@2.117.2';
import contrato from './contrato.json' with { type: 'json' };
import { tratarEnvio } from './logica.js';

Deno.serve(async (req: Request) => {
  const env = Deno.env.toObject();
  const chave = env.SUPABASE_SERVICE_ROLE_KEY || env.RNQ_CHAVE_SECRETA;
  const db = createClient(env.SUPABASE_URL, chave, { auth: { persistSession: false } });
  const r = await tratarEnvio({
    metodo: req.method,
    url: req.url,
    corpo: req.method === 'POST' ? await req.text() : '',
    env,
    contrato,
    buscarComunidades: async () => {
      const { data, error } = await db.from('comunidades').select('id,nome,nome_en');
      if (error) throw error;
      return data;
    },
    gravar: async (itens: unknown[]) => {
      const { data, error } = await db.rpc('rnq_receber_envio', { p: { itens } });
      if (error) throw error;
      return data;
    },
  }).catch((e: Error) => ({ status: 500, json: { erro: e.message } }));
  return new Response(JSON.stringify(r.json), { status: r.status, headers: { 'Content-Type': 'application/json' } });
});
