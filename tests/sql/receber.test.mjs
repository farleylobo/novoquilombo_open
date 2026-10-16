// Edge Function "receber": a porta de entrada (chave secreta, site, formato). A montagem dos itens é comparada
// com o pipeline Python em tests/test_receber.py.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { tratarEnvio, brasilia, chaveNome } from '../../admin/supabase/functions/receber/logica.js';

const contrato = JSON.parse(fs.readFileSync(new URL('../../admin/supabase/functions/receber/contrato.json', import.meta.url)));
const SEGREDO = 'segredo-de-teste-com-mais-de-24-caracteres';
const ENV = { RNQ_RECEBER_SEGREDO: SEGREDO, RNQ_SITE_NOME: 'mapa-novoquilombo' };
const corpo = (extra = {}) => JSON.stringify({ id: 'n-1', form_name: 'participar', site_name: 'mapa-novoquilombo',
  created_at: '2026-10-16T19:13:11.315Z', data: { nome: 'Ana Teste', contato: 'ana@exemplo.org', comunidades: ['ESG'],
  visibilidade: 'mapa', maior_18: 'sim', mural: 'sim', pedido: 'Preciso de mentoria' }, ...extra });

function chamar({ url = `https://x.supabase.co/functions/v1/receber?chave=${SEGREDO}`, metodo = 'POST', c = corpo(), env = ENV } = {}) {
  const gravados = [];
  return tratarEnvio({ metodo, url, corpo: c, env, contrato,
    buscarComunidades: async () => [{ id: 'esg', nome: 'ESG', nome_en: 'ESG' }],
    gravar: async (itens) => { gravados.push(...itens); return { novos: itens.length }; } })
    .then(r => ({ ...r, gravados }));
}

test('envio do "Faça parte" vira cadastro + pedido no mural, pendentes, com o contato no privado', async () => {
  const r = await chamar();
  assert.equal(r.status, 200);
  assert.equal(r.json.novos, 2);
  const [cad, ped] = r.gravados;
  assert.equal(cad.tipo, 'cadastro');
  assert.equal(cad.titulo, 'Ana Teste');
  assert.deepEqual(cad.comunidades, ['esg']);
  assert.equal(cad.recebido_em, '2026-10-16T16:13:00-03:00');
  assert.ok(!JSON.stringify(cad.conteudo).includes('ana@exemplo.org'));
  assert.ok(JSON.stringify(cad.privado).includes('ana@exemplo.org'));
  assert.equal(ped.item_id, 'n-1-pedido');
  assert.equal(ped.titulo, 'Pedido: Preciso de mentoria');
});

test('sem a chave certa, nada entra', async () => {
  for (const url of ['https://x/functions/v1/receber', 'https://x/functions/v1/receber?chave=errada',
                     `https://x/functions/v1/receber?chave=${SEGREDO}x`]) {
    const r = await chamar({ url });
    assert.equal(r.status, 401);
    assert.equal(r.gravados.length, 0);
  }
  const semSegredo = await chamar({ env: { RNQ_RECEBER_SEGREDO: 'curto' }, url: 'https://x/?chave=curto' });
  assert.equal(semSegredo.status, 401, 'segredo fraco ou ausente recusa tudo');
});

test('outro site, método errado, JSON inválido, robô e formulário sem moderação', async () => {
  assert.equal((await chamar({ c: corpo({ site_name: 'outro-site' }) })).status, 403);
  assert.equal((await chamar({ metodo: 'GET' })).status, 405);
  assert.equal((await chamar({ c: '{quebrado' })).status, 400);
  assert.equal((await chamar({ c: 'x'.repeat(70000) })).status, 413);
  const robo = await chamar({ c: corpo({ data: { nome: 'x', bot: 'sou robô' } }) });
  assert.equal(robo.gravados.length, 0);
  const saida = await chamar({ c: corpo({ form_name: 'opt-out', data: { nome: 'x' } }) });
  assert.equal(saida.status, 200);
  assert.equal(saida.gravados.length, 0, 'saídas seguem pelo Mac (RF8)');
});

test('utilitários: horário de Brasília e nomes sem acento', () => {
  assert.deepEqual(brasilia('2026-01-01T02:30:00Z'), { texto: '2025-12-31 23:30', iso: '2025-12-31T23:30:00-03:00' });
  assert.equal(chaveNome('  Comunicação & Mídia '), 'comunicacao midia');
});
