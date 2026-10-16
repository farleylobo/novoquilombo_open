// Edge Function "convidar" (Supabase). Publicada por "python3 painel_admin.py configurar".
// Toda a lógica está em logica.js (testada no Node); aqui só a ligação com o Deno.
import { createClient } from 'npm:@supabase/supabase-js@2.117.2';
import { tratarConvite } from './logica.js';

Deno.serve(async (req: Request) => {
  let corpo = null;
  if (req.method === 'POST') {
    try { corpo = await req.json(); } catch (_) { corpo = null; }
  }
  const r = await tratarConvite({
    metodo: req.method,
    origem: req.headers.get('origin'),
    autorizacao: req.headers.get('authorization'),
    corpo,
    env: Deno.env.toObject(),
    criarCliente: createClient,
  });
  return new Response(r.json === undefined ? null : JSON.stringify(r.json), { status: r.status, headers: r.headers });
});
