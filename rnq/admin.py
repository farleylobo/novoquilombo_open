"""Painel admin com login (SPEC-RNQ-003): o que o pipeline do Mac manda para o Supabase e o que traz de volta.

Fluxo (python3 atualizar.py, com SUPABASE_URL e SUPABASE_SECRET_KEY no .env):
1. buscar as decisões de moderação do painel (rnq_pipeline_decisoes);
2. aplicar_decisoes(): as decisões do painel valem no lugar de "Publicar?", "Incluir no mapa?" etc. (D5);
3. o export de sempre gera o site com essas decisões;
4. montar_sincronizacao(): itens de moderação (com as comunidades de cada um), comunidades e snapshots do painel
   (rede toda + um por comunidade, PT e EN) -> rnq_pipeline_sincronizar.

Privacidade: o snapshot de uma comunidade é montado só com as pessoas e as linhas da planilha daquela comunidade
(recortar()). Assim um tecelão nunca recebe contatos de outra comunidade, nem baixando o dado direto (RF21).
"""
import json
import os
from datetime import datetime, timedelta, timezone

from . import config as C
from . import painel
from .rede import metricas, sugerir_apresentacoes
from .supabase import Banco, ErroSupabase
from .tecelagem import ABAS
from .util import chave_nome, data_iso, dividir, dividir_areas, id_estavel, nao, sim, slug, txt

FUSO = timezone(timedelta(hours=-3))          # horário de Brasília (sem horário de verão desde 2019)

# tipo -> (aba da planilha, coluna da decisão, prefixo do id estável, colunas que identificam uma linha sem ID)
TIPOS = {
    'mural': ('Mural', 'Publicar?', 'm', ('Tipo', 'Título', 'Nome')),
    'perfil': ('Perfis', 'Publicar?', 'p', ('Pessoa no mapa', 'Recebido em', 'Posso compartilhar', 'Quero aprender')),
    'ligacao': ('Ligações sugeridas', 'Aprovar?', 'l', ('Pessoa', 'Quem sugere')),
    'iniciativa': ('Iniciativas', 'Publicar?', 'i', ('Tipo', 'Título', 'Nome de quem propôs')),
    'cadastro': ('Cadastros', 'Incluir no mapa?', 'c', ('Nome', 'Recebido em')),
    'resposta': ('Respostas do mural', 'Apresentação feita?', 'r', ('ID do item', 'Nome', 'Recebido em')),
    'participacao': ('Participações', 'Encaminhado?', 'pa', ('ID da iniciativa', 'Nome', 'Recebido em')),
}
ABA_DO_TIPO = {t: v[0] for t, v in TIPOS.items()}
# Colunas que já estão no título do item (não se repetem nos campos do cartão)
NO_TITULO = {'mural': ('Tipo', 'Título'), 'perfil': ('Pessoa no mapa',), 'ligacao': ('Pessoa', 'Quem sugere'),
             'iniciativa': ('Tipo', 'Título'), 'cadastro': ('Nome',), 'resposta': ('Nome', 'Item'),
             'participacao': ('Nome', 'Iniciativa')}
# Abas que só aparecem no painel da rede toda (não são de nenhuma comunidade e não têm contatos)
ABAS_SO_REDE = ('Saídas', 'Confirmações', 'Papéis', 'Correções')


# ---------------------------------------------------------------- configuração
def chave_secreta(cfg):
    return cfg.get('SUPABASE_SECRET_KEY') or cfg.get('SUPABASE_SERVICE_ROLE_KEY') or ''


def configurado(cfg):
    return bool(cfg.get('SUPABASE_URL') and chave_secreta(cfg))


def banco(cfg, abrir=None):
    """Banco do painel, ou None se o .env não tem o Supabase (o pipeline segue como antes, só com a planilha)."""
    if not configurado(cfg):
        return None
    return Banco(cfg['SUPABASE_URL'], chave_secreta(cfg), **({'abrir': abrir} if abrir else {}))


# ---------------------------------------------------------------- itens de moderação
def item_id(tipo, linha):
    aba, _, prefixo, cols = TIPOS[tipo]
    return txt(linha.get('ID')) or id_estavel(prefixo, *(linha.get(c) for c in cols))


def status_da_planilha(tipo, valor):
    if sim(valor):
        return 'aprovado'
    if nao(valor):
        return 'recusado'
    return 'pendente'


def valor_para_planilha(status):
    return {'aprovado': 'Sim', 'recusado': 'Não'}.get(status)


def _titulo(tipo, r):
    t = {
        'mural': f'{txt(r.get("Tipo")) or "Item"}: {txt(r.get("Título"))}',
        'perfil': txt(r.get('Pessoa no mapa')),
        'ligacao': f'{txt(r.get("Pessoa"))} ↔ {txt(r.get("Quem sugere"))}',
        'iniciativa': f'{txt(r.get("Tipo")) or "Iniciativa"}: {txt(r.get("Título"))}',
        'cadastro': txt(r.get('Nome')),
        'resposta': f'{txt(r.get("Nome"))} → {txt(r.get("Item"))}',
        'participacao': f'{txt(r.get("Nome"))} → {txt(r.get("Iniciativa"))}',
    }[tipo]
    return t.strip(' :→↔') or '(sem título)'


def aplicar_decisoes(tec, decisoes):
    """Devolve (tec com as decisões do painel nas colunas de moderação, avisos). Não altera a planilha.
    Item que ainda não chegou ao painel (novo na planilha) segue com o valor da planilha até a sincronização."""
    if decisoes is None:
        return tec, []
    mapa = {(d['tipo'], d['item_id']): d for d in decisoes}
    novo = {aba: [dict(r) for r in linhas] for aba, linhas in (tec or {}).items()}
    avisos = []
    for tipo, (aba, col, _, _) in TIPOS.items():
        for r in novo.get(aba, []):
            d = mapa.get((tipo, item_id(tipo, r)))
            if not d:
                continue
            antes = r.get(col)
            if txt(antes) and status_da_planilha(tipo, antes) != d['status']:
                avisos.append(f'{aba} "{_titulo(tipo, r)}": a planilha diz "{txt(antes)}", mas no painel está '
                              f'"{d["status"]}" — vale o painel (a coluna "{col}" não é mais usada)')
            r[col] = valor_para_planilha(d['status'])
    return novo, avisos


class Comunidades:
    """Descobre de quais comunidades (ids) é cada pessoa, área ou linha da planilha."""

    def __init__(self, pub, interno):
        self.idx = interno['indice']
        self.de_id = {p['id']: list(p.get('comunidades') or []) for p in pub['pessoas']}
        nomes = pub.get('listas', {}).get('comunidades') or pub['comunidades']
        self.por_nome = {}
        for c in nomes:
            self.por_nome[chave_nome(c['nome'])] = c['id']
            if c.get('nome_en'):
                self.por_nome.setdefault(chave_nome(c['nome_en']), c['id'])
        for tema, com in C.TEMA_PARA_COMUNIDADE.items():
            self.por_nome.setdefault(chave_nome(tema), slug(com))
        for antigo, novo in C.RENOMEAR_TEMA.items():
            if novo in C.TEMA_PARA_COMUNIDADE:
                self.por_nome.setdefault(chave_nome(antigo), slug(C.TEMA_PARA_COMUNIDADE[novo]))

    def pessoa(self, nome):
        return self.de_id.get(self.idx.achar(nome), []) if txt(nome) else []

    def pessoa_id(self, pid):
        return self.de_id.get(pid, [])

    def areas(self, valor):
        return [self.por_nome[k] for k in (chave_nome(a) for a in dividir_areas(valor)) if k in self.por_nome]

    def nomes_areas(self, nomes):
        return [self.por_nome[k] for k in (chave_nome(a) for a in nomes or []) if k in self.por_nome]


def comunidades_das_linhas(tec, com):
    """{(tipo, item_id): [ids de comunidade]} para todas as linhas moderáveis da planilha."""
    out = {}
    mural = {}
    for r in tec.get('Mural', []):
        cs = com.areas(r.get('Áreas')) + com.pessoa(r.get('Está no mapa como')) + com.pessoa(r.get('Nome'))
        out[('mural', item_id('mural', r))] = cs
        mural[txt(r.get('ID'))] = cs
    inis = {}
    for r in tec.get('Iniciativas', []):
        cs = com.areas(r.get('Áreas')) + com.pessoa(r.get('Nome de quem propôs'))
        for p in dividir(r.get('Participantes')):
            cs += com.pessoa(p)
        out[('iniciativa', item_id('iniciativa', r))] = cs
        inis[txt(r.get('ID'))] = cs
    for r in tec.get('Perfis', []):
        out[('perfil', item_id('perfil', r))] = com.pessoa(r.get('Pessoa no mapa'))
    for r in tec.get('Ligações sugeridas', []):
        out[('ligacao', item_id('ligacao', r))] = com.pessoa(r.get('Pessoa')) + com.pessoa(r.get('Quem sugere'))
    for r in tec.get('Cadastros', []):
        out[('cadastro', item_id('cadastro', r))] = (com.areas(r.get('Comunidades')) + com.areas(r.get('Temas'))
                                                     + com.pessoa(r.get('Nome')))
    for r in tec.get('Respostas do mural', []):
        out[('resposta', item_id('resposta', r))] = mural.get(txt(r.get('ID do item')), []) + com.pessoa(r.get('Nome'))
    for r in tec.get('Participações', []):
        out[('participacao', item_id('participacao', r))] = (inis.get(txt(r.get('ID da iniciativa')), [])
                                                             + com.pessoa(r.get('Nome')))
    return {k: sorted(set(v)) for k, v in out.items()}


def _quando(v):
    """'2026-10-06 10:00' (horário de Brasília, como o sincronizador grava) -> ISO com fuso; None se não der."""
    if isinstance(v, datetime):
        return (v if v.tzinfo else v.replace(tzinfo=FUSO)).isoformat()
    s = txt(v).replace('T', ' ')
    for fmt, n in (('%Y-%m-%d %H:%M:%S', 19), ('%Y-%m-%d %H:%M', 16), ('%Y-%m-%d', 10),
                   ('%d/%m/%Y %H:%M', 16), ('%d/%m/%Y', 10)):
        try:
            return datetime.strptime(s[:n], fmt).replace(tzinfo=FUSO).isoformat()
        except ValueError:
            continue
    return None


def _bloqueio(tipo, r):
    """RF26: cadastro só pode ser aprovado se a pessoa escolheu aparecer e tem 18 anos ou mais."""
    if tipo != 'cadastro':
        return []
    alertas = []
    if chave_nome(r.get('Visibilidade')) not in ('mapa', ''):
        alertas.append('fora_do_mapa')
    if not sim(r.get('18 anos ou mais')):
        alertas.append('sem_18')
    return alertas


# Colunas com o nome de quem está envolvido em cada linha (para RF25: quem saiu do mapa some do painel também)
COLUNAS_PESSOA = ('Nome', 'Está no mapa como', 'Pessoa no mapa', 'Pessoa', 'Quem sugere', 'Nome de quem propôs')


def sem_saidas(tec):
    """RF25: tira da planilha (em memória) as linhas de quem pediu para sair do mapa. O painel nunca guarda
    contatos de quem saiu; na sincronização seguinte, os itens dessas pessoas são apagados do banco."""
    sair = {chave_nome(r.get('Nome')) for r in (tec or {}).get('Saídas', [])
            if txt(r.get('Nome')) and not nao(r.get('Remover?'))}
    if not sair:
        return tec
    return {aba: (linhas if aba == 'Saídas' else
                  [r for r in linhas if not any(chave_nome(r.get(c)) in sair for c in COLUNAS_PESSOA if txt(r.get(c)))])
            for aba, linhas in tec.items()}


def alvo_no_mapa(tipo, r, pub, interno):
    """Trecho do link direto no mapa público ('p/<pessoa>', 'm/<item>' ou 'i/<iniciativa>') quando o alvo está nos
    dados gerados nesta atualização; senão None. (O mapa no ar mostra a última versão publicada com publicar.py.)"""
    idx = interno['indice']
    pessoas = {p['id'] for p in pub['pessoas']}
    mural = {m['id'] for m in pub['mural']}
    inis = {i['id'] for i in pub['iniciativas']}

    def pessoa(*cols):
        for c in cols:
            pid = idx.achar(r.get(c)) if txt(r.get(c)) else None
            if pid in pessoas:
                return 'p/' + pid
        return None
    if tipo == 'mural':
        return 'm/' + item_id(tipo, r) if item_id(tipo, r) in mural else pessoa('Está no mapa como', 'Nome')
    if tipo == 'iniciativa':
        return 'i/' + item_id(tipo, r) if item_id(tipo, r) in inis else pessoa('Nome de quem propôs')
    if tipo == 'resposta':
        return 'm/' + txt(r.get('ID do item')) if txt(r.get('ID do item')) in mural else None
    if tipo == 'participacao':
        return 'i/' + txt(r.get('ID da iniciativa')) if txt(r.get('ID da iniciativa')) in inis else None
    return pessoa({'perfil': 'Pessoa no mapa', 'ligacao': 'Pessoa', 'cadastro': 'Nome'}[tipo])


def itens_moderacao(tec, pub, interno):
    """Itens para a aba Moderação do painel: conteúdo (o que iria ao site) separado do privado (contatos e notas)."""
    com = Comunidades(pub, interno)
    coms = comunidades_das_linhas(tec, com)
    itens = []
    for tipo, (aba, col, _, _) in TIPOS.items():
        colunas = {nome: t for nome, _, t, _ in ABAS[aba][1]}
        vistos = set()
        for r in tec.get(aba, []):
            iid = item_id(tipo, r)
            if iid in vistos:              # linha repetida na planilha: um item só
                continue
            vistos.add(iid)
            campos, privado = [], []
            for nome, valor in r.items():
                v = txt(valor)
                if not v or nome in ('ID', 'Recebido em', col) or nome in NO_TITULO[tipo]:
                    continue
                tipo_col = colunas.get(nome, 'editar')
                (privado if tipo_col in ('privado', 'interno') else campos).append([nome, v])
            alertas = _bloqueio(tipo, r)
            itens.append({
                'tipo': tipo, 'item_id': iid, 'comunidades': coms.get((tipo, iid), []),
                'titulo': _titulo(tipo, r)[:200],
                'conteudo': {'aba': aba, 'coluna': col, 'campos': campos, 'alertas': alertas,
                             'bloqueio': alertas[0] if alertas else None,
                             'mapa': alvo_no_mapa(tipo, r, pub, interno)},
                'privado': {'campos': privado},
                'recebido_em': _quando(r.get('Recebido em')),
                'status_planilha': status_da_planilha(tipo, r.get(col)),
            })
    return itens


# ---------------------------------------------------------------- recorte por comunidade
def _coms_publicas(item, com, chave_pessoas):
    cs = com.nomes_areas(item.get('areas'))
    for k in chave_pessoas:
        v = item.get(k)
        for pid in (v if isinstance(v, list) else [v]):
            cs += com.pessoa_id(pid)
    return set(cs)


def recortar(pub, interno, tec, comunidade_id):
    """(pub, interno, tec, sugestoes) só com o que é da comunidade. Nada de contatos de outras comunidades."""
    com = Comunidades(pub, interno)
    dentro = {p['id'] for p in pub['pessoas'] if comunidade_id in (p.get('comunidades') or [])}
    pessoas = [p for p in pub['pessoas'] if p['id'] in dentro]
    ligs = [l for l in pub['ligacoes'] if l['a'] in dentro and l['b'] in dentro]
    mural = [m for m in pub['mural'] if comunidade_id in _coms_publicas(m, com, ('autor_id',))]
    inis = [i for i in pub['iniciativas']
            if comunidade_id in _coms_publicas(i, com, ('proponente_id', 'participantes'))]
    pub_c = dict(pub, pessoas=pessoas, ligacoes=ligs, mural=mural, iniciativas=inis)
    pares = [(l['a'], l['b']) for l in ligs]
    hub = interno.get('hub') if interno.get('hub') in dentro else None
    met = metricas(pessoas, pares, hub_id=hub)
    pub_c['estatisticas'] = dict(
        pub['estatisticas'], pessoas=len(pessoas), ligacoes=len(ligs), comunidades=1,
        organizacoes=len({chave_nome(p['organizacao']) for p in pessoas if p.get('organizacao')}),
        pct_conectadas=round(met['pct_conectadas'] * 100),
        mural_abertos=sum(1 for m in mural if m['status'] == 'aberto'),
        iniciativas_ativas=sum(1 for i in inis if i['status'] == 'ativa'))

    coms = comunidades_das_linhas(tec, com)
    tec_c = {}
    for aba, linhas in tec.items():
        tipo = next((t for t, a in ABA_DO_TIPO.items() if a == aba), None)
        if tipo:
            tec_c[aba] = [r for r in linhas if comunidade_id in coms.get((tipo, item_id(tipo, r)), [])]
        elif aba == 'Apresentações':
            idx = interno['indice']
            tec_c[aba] = [r for r in linhas
                          if idx.achar(r.get('Pessoa A')) in dentro or idx.achar(r.get('Pessoa B')) in dentro]
        else:
            tec_c[aba] = []                 # Saídas, Confirmações, Papéis, Correções: só na rede toda
    ja = [x for x in interno.get('ja_apresentadas', []) if x[0] in dentro and x[1] in dentro]
    desejos = [x for x in interno.get('desejos', []) if x[0] in dentro and x[1] in dentro]
    interno_c = {'indice': interno['indice'], 'hub': hub, 'metricas': met, 'desejos': desejos, 'ja_apresentadas': ja,
                 'recorte': comunidade_id}
    sug = sugerir_apresentacoes(
        pessoas, pares, ja_feitas=ja, desejos=desejos, hub_id=interno.get('hub'), n=15,
        nomes_temas={t['id']: t['nome'] for t in pub['temas']},
        nomes_coms={x['id']: x['nome'] for x in pub['comunidades']},
        nomes_atu={a['id']: a['nome'] for a in pub.get('atuacoes', [])})
    return pub_c, interno_c, tec_c, sug


# ---------------------------------------------------------------- snapshots
def registrar_historico(pasta, escopo, met, agora):
    """Evolução por escopo (rede/comunidade) em _trabalho/historico-painel/<escopo>.json (privado, no Mac)."""
    if not pasta:
        return []
    caminho = os.path.join(pasta, f'{slug(escopo) or "rede"}.json')
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
    os.makedirs(pasta, exist_ok=True)
    with open(caminho, 'w', encoding='utf-8') as fh:
        json.dump(hist, fh, ensure_ascii=False, indent=1)
    return hist


def _resumo(pub, interno, tec, sug, nome_pt, nome_en):
    met = interno['metricas']
    from .rede import FASES, FASES_EN
    return {
        'nome': {'pt': nome_pt, 'en': nome_en},
        'pessoas': met['pessoas'], 'ligacoes': met['ligacoes'], 'conectadas': met['conectadas'],
        'pct_conectadas': round(met['pct_conectadas'], 4), 'dependencia_hub': round(met['dependencia_hub'], 4),
        'isolados': len(met['isolados']), 'grupos': len(met['grupos']),
        'fase': met['fase'], 'fase_nome': {'pt': FASES[met['fase']][0], 'en': FASES_EN[met['fase']][0]},
        'pendentes': sum(q for _, _, q in painel.pendencias(tec)),
        'sugestoes': len(sug), 'mural_abertos': pub['estatisticas'].get('mural_abertos', 0),
    }


def montar_snapshots(pub, interno, tec, sug, avisos, historico, agora, site_url='', pasta_hist=None):
    rede_pt, rede_en = painel.TEXTOS['pt']['escopo_rede'], painel.TEXTOS['en']['escopo_rede']
    snaps = [{
        'escopo': 'rede', 'resumo': _resumo(pub, interno, tec, sug, rede_pt, rede_en),
        'html_pt': painel.gerar(pub, interno, tec, sug, avisos, historico, agora, site_url, 'pt', 'painel', rede_pt),
        'html_en': painel.gerar(pub, interno, tec, sug, avisos, historico, agora, site_url, 'en', 'painel', rede_en),
    }]
    for c in pub['comunidades']:
        pub_c, interno_c, tec_c, sug_c = recortar(pub, interno, tec, c['id'])
        if not pub_c['pessoas']:
            continue
        hist = registrar_historico(pasta_hist, c['id'], interno_c['metricas'], agora) if pasta_hist else []
        n_pt, n_en = c['nome'], c.get('nome_en') or c['nome']
        snaps.append({
            'escopo': c['id'], 'resumo': _resumo(pub_c, interno_c, tec_c, sug_c, n_pt, n_en),
            'html_pt': painel.gerar(pub_c, interno_c, tec_c, sug_c, None, hist, agora, site_url, 'pt', 'painel', n_pt),
            'html_en': painel.gerar(pub_c, interno_c, tec_c, sug_c, None, hist, agora, site_url, 'en', 'painel', n_en),
        })
    return snaps


def montar_sincronizacao(pub, interno, tec, sug, avisos, historico, agora, site_url='', pasta_hist=None):
    """O pacote completo para rnq_pipeline_sincronizar (ver admin/supabase/schema.sql)."""
    agora = agora or datetime.now()
    tec = sem_saidas(tec)
    if pasta_hist:
        registrar_historico(pasta_hist, 'rede', interno['metricas'], agora)
    comunidades = [{'id': c['id'], 'nome': c['nome'], 'nome_en': c.get('nome_en') or ''}
                   for c in (pub.get('listas', {}).get('comunidades') or pub['comunidades'])]
    return {
        'gerado_em': (agora if agora.tzinfo else agora.replace(tzinfo=FUSO)).isoformat(),
        'comunidades': comunidades,
        'itens': itens_moderacao(tec, pub, interno),
        'snapshots': montar_snapshots(pub, interno, tec, sug, avisos, historico, agora, site_url, pasta_hist),
    }


# ---------------------------------------------------------------- uso pelo pipeline
def buscar_decisoes(cfg, abrir=None):
    """Decisões do painel, ou None se o painel não está configurado. Levanta ErroSupabase se não conseguir ler:
    com o painel como fonte da moderação, gerar o site sem as decisões poderia publicar o que foi recusado."""
    b = banco(cfg, abrir)
    if not b:
        return None
    d = b.rpc('rnq_pipeline_decisoes')
    if not isinstance(d, list):
        raise ErroSupabase('Resposta inesperada do banco do painel (rnq_pipeline_decisoes)')
    return d


def sincronizar(cfg, contexto, abrir=None, pasta_hist=None):
    """Manda itens, comunidades e snapshots. contexto: o dict preenchido por exportar.executar(contexto=...)."""
    b = banco(cfg, abrir)
    if not b:
        return None
    pacote = montar_sincronizacao(contexto['pub'], contexto['interno'], contexto['tec'], contexto['sug'],
                                  contexto['avisos'], contexto['historico'], contexto['agora'],
                                  contexto.get('site_url', ''), pasta_hist)
    return b.rpc('rnq_pipeline_sincronizar', {'p': pacote}, timeout=300)


__all__ = ['TIPOS', 'ErroSupabase', 'aplicar_decisoes', 'buscar_decisoes', 'configurado', 'itens_moderacao',
           'montar_sincronizacao', 'montar_snapshots', 'recortar', 'sincronizar']


# ---------------------------------------------------------------- chegada na hora (Edge Function "receber")
def contrato():
    """Regras que a Edge Function "receber" usa para montar, na hora, o item de moderação de um envio do site —
    tiradas das mesmas tabelas do pipeline (tecelagem.FORMULARIOS/ABAS, TIPOS), para o item ficar igual ao que a
    planilha gera depois. Vai junto com a função (admin/supabase/functions/receber/contrato.json)."""
    from .tecelagem import FORMULARIOS
    tema_com = {}
    for tema, com in C.TEMA_PARA_COMUNIDADE.items():
        tema_com[chave_nome(tema)] = slug(com)
    for antigo, novo in C.RENOMEAR_TEMA.items():
        if novo in C.TEMA_PARA_COMUNIDADE:
            tema_com[chave_nome(antigo)] = slug(C.TEMA_PARA_COMUNIDADE[novo])
    tipo_da_aba = {a: t for t, a in ABA_DO_TIPO.items()}
    return {
        'versao': 1,
        'formularios': {f: {'aba': aba, 'tipo': tipo_da_aba.get(aba), 'campos': mapa, 'padrao': padrao}
                        for f, (aba, mapa, padrao) in FORMULARIOS.items()},
        'colunas': {aba: [[nome, tipo] for nome, _, tipo, _ in cols] for aba, (_, cols) in ABAS.items()},
        'tipos': {t: {'aba': v[0], 'coluna': v[1]} for t, v in TIPOS.items()},
        'no_titulo': {t: list(v) for t, v in NO_TITULO.items()},
        'tema_comunidade': tema_com,
    }


def gravar_contrato(destino):
    with open(destino, 'w', encoding='utf-8') as fh:
        json.dump(contrato(), fh, ensure_ascii=False, indent=1, sort_keys=True)
    return destino
