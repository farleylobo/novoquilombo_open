"""Export da visão pública da RNQ.

Lê as três planilhas e gera:
- site/rnq-publico.json e site/data.js  (público — só campos da lista fechada, RF3/CA1)
- painel/painel-tecelagem.html          (privado — saúde da rede, apresentações sugeridas, fila de moderação)
- painel/painel-tecelagem-en.html       (privado — o mesmo painel em inglês)
- _trabalho/historico-rede.json         (privado — evolução das métricas a cada atualização)

Com o painel admin configurado (SUPABASE_URL e SUPABASE_SECRET_KEY no .env), as decisões de moderação vêm do
painel (veja docs/PAINEL-ADMIN.md): sem conexão com o painel, nada é gerado.

Uso: python3 exportar.py            (ou python3 atualizar.py para sincronizar formulários e o painel admin)
     python3 exportar.py --exemplo  (rede fictícia, para quem clonou o projeto e não tem as planilhas)
"""
import argparse
import json
import os
import sys
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from rnq import admin, fontes, netlify, painel, publico, tecelagem  # noqa: E402
from rnq.rede import sugerir_apresentacoes  # noqa: E402
from rnq.config import HUB_NOME  # noqa: E402

# Ao criar a planilha de tecelagem pela primeira vez: o hub (rnq/config.py) já entra com seus papéis.
# Correções de nomes/cargos de pessoas reais ficam só na planilha (aba Correções), nunca no código.
CORRECOES_INICIAIS = []
PAPEIS_INICIAIS = [{'Pessoa': HUB_NOME, 'Papel 1': 'Conector(a)', 'Papel 2': 'Guardiã(o) da rede'}]


def escrever(caminho, texto):
    with open(caminho, 'w', encoding='utf-8') as fh:
        fh.write(texto)


def caminhos(pasta):
    return {
        'selecao': os.path.join(pasta, 'RNQ-selecao.xlsx'),
        'temas': os.path.join(pasta, 'RNQ-temas-atuacao.xlsx'),
        'tecelagem': os.path.join(pasta, 'RNQ-tecelagem.xlsx'),
        'site': os.path.join(pasta, 'site'),
        'painel': os.path.join(pasta, 'painel', 'painel-tecelagem.html'),
        'painel_en': os.path.join(pasta, 'painel', 'painel-tecelagem-en.html'),
        'historico': os.path.join(pasta, '_trabalho', 'historico-rede.json'),
    }


def registrar_historico(caminho, met, agora):
    hist = []
    if os.path.exists(caminho):
        try:
            with open(caminho, encoding='utf-8') as fh:
                hist = json.load(fh)
        except ValueError:
            hist = []
    dia = agora.strftime('%Y-%m-%d')
    hist = [h for h in hist if h.get('data') != dia]
    hist.append({'data': dia, 'pessoas': met['pessoas'], 'ligacoes': met['ligacoes'],
                 'pct_conectadas': met['pct_conectadas'], 'dependencia_hub': met['dependencia_hub'],
                 'grupos': len(met['grupos']), 'fase': met['fase'], 'fase_nome': met['fase_nome']})
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    escrever(caminho, json.dumps(hist, ensure_ascii=False, indent=1))
    return hist


def executar(pasta=AQUI, agora=None, sem_painel=False, silencioso=False, site=None, exemplo=False,
             decisoes=None, contexto=None):
    """decisoes: decisões de moderação do painel admin (rnq_pipeline_decisoes); valem no lugar das colunas da
    planilha. contexto: dict opcional que recebe o que o painel admin precisa para sincronizar."""
    agora = agora or datetime.now()
    c = caminhos(pasta)
    if site:
        c['site'] = site
    tecelagem.garantir(c['tecelagem'], papeis_iniciais=PAPEIS_INICIAIS, correcoes_iniciais=CORRECOES_INICIAIS)
    sel = fontes.ler_selecao(c['selecao'])
    tem = fontes.ler_temas(c['temas'])
    tec, avisos_painel = admin.aplicar_decisoes(fontes.ler_tecelagem(c['tecelagem']), decisoes)
    pub, avisos, interno = publico.montar(sel, tem, tec, agora)
    avisos = avisos_painel + avisos

    os.makedirs(c['site'], exist_ok=True)
    js = json.dumps(pub, ensure_ascii=False, indent=1)
    escrever(os.path.join(c['site'], 'rnq-publico.json'), js)
    escrever(os.path.join(c['site'], 'data.js'), 'window.RNQ_DATA = ' + js + ';\n')
    marca = os.path.join(c['site'], '.exemplo')       # publicar.py recusa publicar a rede fictícia
    if exemplo:
        escrever(marca, 'site gerado com a rede fictícia de exemplo\n')
    elif os.path.exists(marca):
        os.remove(marca)

    sug = sugerir_apresentacoes(
        pub['pessoas'], [(l['a'], l['b']) for l in pub['ligacoes']],
        ja_feitas=interno['ja_apresentadas'], desejos=interno['desejos'], hub_id=interno['hub'], n=15,
        nomes_temas={t['id']: t['nome'] for t in pub['temas']},
        nomes_coms={x['id']: x['nome'] for x in pub['comunidades']},
        nomes_atu={a['id']: a['nome'] for a in pub['atuacoes']})
    hist = registrar_historico(c['historico'], interno['metricas'], agora)
    site_url = netlify.ler_env(pasta).get('RNQ_SITE_URL', '')
    if contexto is not None:
        contexto.update(pub=pub, avisos=avisos, interno=interno, sug=sug, tec=tec, historico=hist, agora=agora,
                        site_url=site_url, pasta_hist=os.path.join(pasta, '_trabalho', 'historico-painel'))
    if not sem_painel:
        os.makedirs(os.path.dirname(c['painel']), exist_ok=True)
        escrever(c['painel'], painel.gerar(pub, interno, tec, sug, avisos, hist, agora, site_url))
        escrever(c['painel_en'], painel.gerar(pub, interno, tec, sug, avisos, hist, agora, site_url, idioma='en'))

    e, m = pub['estatisticas'], interno['metricas']
    if not silencioso:
        print(f"OK: {e['pessoas']} pessoas, {e['comunidades']} comunidades, {e['temas']} temas, "
              f"{e['ligacoes']} ligações, {e['organizacoes']} organizações")
        print(f"    Mural: {len(pub['mural'])} publicados ({e['mural_abertos']} abertos) · "
              f"Iniciativas: {len(pub['iniciativas'])}")
        print(f"    Saúde: {m['fase_nome']} · {e['pct_conectadas']}% conectadas · "
              f"dependência do hub {round(m['dependencia_hub'] * 100)}% · {len(sug)} apresentações sugeridas")
        for a in avisos:
            print('AVISO:', a)
    return pub, avisos, interno, sug


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--sem-painel', action='store_true', help='não gera o painel do tecelão')
    ap.add_argument('--exemplo', action='store_true', help='gera o site com uma rede fictícia (sem dados reais)')
    a = ap.parse_args()
    try:
        if a.exemplo:
            from exemplo.gerar_exemplo import gerar
            pasta_ex = gerar(os.path.join(AQUI, '_trabalho', 'exemplo'))
            executar(pasta=pasta_ex, sem_painel=a.sem_painel, site=os.path.join(AQUI, 'site'), exemplo=True)
            print('Site gerado com a rede FICTÍCIA de exemplo. Para os dados reais: python3 exportar.py')
        else:
            try:
                decisoes = admin.buscar_decisoes(netlify.ler_env(AQUI))
            except admin.ErroSupabase as err:
                print('Painel admin sem conexão — nada foi gerado (as decisões de moderação estão lá):', err)
                sys.exit(3)
            executar(sem_painel=a.sem_painel, decisoes=decisoes)
    except publico.ErroPrivacidade as err:
        print('ERRO DE PRIVACIDADE — nada foi publicado:', err)
        sys.exit(2)
