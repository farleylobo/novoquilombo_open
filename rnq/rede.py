"""Saúde da rede e sugestões de apresentação, inspiradas em June Holley e Valdis Krebs.

- "Conheça a rede, depois teça a rede": as métricas mostram onde a rede está; as sugestões dizem quem apresentar.
- Fases de crescimento (Holley/Krebs): fragmentos dispersos -> hub-and-spoke -> multi-hub -> núcleo/periferia.
- "Conecte pela semelhança, ganhe com a diferença": sugerimos pares com tema em comum (confiança)
  e comunidade/atuação diferentes (novidade). Pares que unem fragmentos ou trazem alguém isolado valem mais.
- Nunca sugerimos o hub atual: o objetivo é a rede depender menos dele.

Tudo em Python puro (sem networkx) para rodar em qualquer máquina.
"""
from collections import deque
from itertools import combinations


def grafo(ids, ligacoes):
    adj = {i: set() for i in ids}
    for a, b in ligacoes:
        if a in adj and b in adj and a != b:
            adj[a].add(b)
            adj[b].add(a)
    return adj


def componentes(adj):
    vistos, comps = set(), []
    for v in adj:
        if v in vistos:
            continue
        comp, fila = set(), deque([v])
        vistos.add(v)
        while fila:
            u = fila.popleft()
            comp.add(u)
            for w in adj[u]:
                if w not in vistos:
                    vistos.add(w)
                    fila.append(w)
        comps.append(comp)
    return sorted(comps, key=len, reverse=True)


def _bfs(adj, origem):
    dist = {origem: 0}
    fila = deque([origem])
    while fila:
        u = fila.popleft()
        for w in adj[u]:
            if w not in dist:
                dist[w] = dist[u] + 1
                fila.append(w)
    return dist


def caminho_medio(adj):
    """Média das distâncias entre pares conectados e o diâmetro (maior distância)."""
    soma = pares = diam = 0
    for v in adj:
        for w, d in _bfs(adj, v).items():
            if w != v:
                soma += d
                pares += 1
                diam = max(diam, d)
    return (soma / pares if pares else 0.0), diam


def intermediacao(adj):
    """Centralidade de intermediação (Brandes), normalizada 0..1. Quem está no caminho entre os outros."""
    cb = {v: 0.0 for v in adj}
    for s in adj:
        pilha, pred = [], {v: [] for v in adj}
        sigma = dict.fromkeys(adj, 0)
        sigma[s] = 1
        dist = dict.fromkeys(adj, -1)
        dist[s] = 0
        fila = deque([s])
        while fila:
            v = fila.popleft()
            pilha.append(v)
            for w in adj[v]:
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    fila.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] += sigma[v]
                    pred[w].append(v)
        delta = dict.fromkeys(adj, 0.0)
        while pilha:
            w = pilha.pop()
            for v in pred[w]:
                delta[v] += sigma[v] / sigma[w] * (1 + delta[w])
            if w != s:
                cb[w] += delta[w]
    n = len(adj)
    escala = 1.0 / ((n - 1) * (n - 2)) if n > 2 else 1.0   # não direcionado: cada par contado 2x
    return {v: c * escala for v, c in cb.items()}


FASES = {
    'fragmentos': ('Fase 1 · Fragmentos dispersos',
                   'A maioria das pessoas ainda não está ligada a ninguém do mapa. Prioridade: apresentar pessoas '
                   'isoladas a alguém com tema em comum.'),
    'hub': ('Fase 2 · Hub-and-spoke',
            'A rede depende de um ponto central. É uma fase necessária, mas temporária: apresente pessoas entre si '
            'sem passar por você e convide outras pessoas a tecer.'),
    'multi-hub': ('Fase 3 · Multi-hub',
                  'Vários conectores ligam grupos entre si. Prioridade: fortalecer pontes entre comunidades e formar '
                  'novos tecelões.'),
    'nucleo': ('Fase 4 · Núcleo e periferia',
               'Há um núcleo denso de confiança e uma periferia aberta. Prioridade: trazer gente nova pela periferia '
               'e ligar a RNQ a outras redes.'),
}


def fase(pct_conectadas, dependencia_hub, caminho):
    if pct_conectadas < 0.4:
        return 'fragmentos'
    if dependencia_hub >= 0.30:
        return 'hub'
    if pct_conectadas >= 0.75 and dependencia_hub < 0.15 and 0 < caminho <= 3.5:
        return 'nucleo'
    return 'multi-hub'


def metricas(pessoas, ligacoes, hub_id=None):
    """pessoas: [{'id', 'comunidades', ...}], ligacoes: [(a, b)]."""
    ids = [p['id'] for p in pessoas]
    adj = grafo(ids, ligacoes)
    n = len(ids)
    m = sum(len(v) for v in adj.values()) // 2
    isolados = [v for v in ids if not adj[v]]
    comps = componentes(adj)
    grupos = [c for c in comps if len(c) > 1]
    med, diam = caminho_medio(adj)
    bc = intermediacao(adj)
    toca_hub = len(adj.get(hub_id, ())) if hub_id in adj else 0
    dependencia = toca_hub / m if m else 0.0
    sem_hub = {v: {w for w in viz if w != hub_id} for v, viz in adj.items() if v != hub_id}
    grupos_sem_hub = [c for c in componentes(sem_hub) if len(c) > 1] if hub_id in adj else grupos
    isolados_sem_hub = sum(1 for v in sem_hub if not sem_hub[v]) if hub_id in adj else len(isolados)
    coms = {p['id']: set(p.get('comunidades') or []) for p in pessoas}
    entre = sum(1 for a in adj for b in adj[a] if a < b and coms[a] and coms[b] and not (coms[a] & coms[b]))
    pct = (n - len(isolados)) / n if n else 0.0
    f = fase(pct, dependencia, med)
    return {
        'pessoas': n, 'ligacoes': m,
        'conectadas': n - len(isolados), 'pct_conectadas': pct,
        'isolados': isolados,
        'grupos': [len(c) for c in grupos],
        'maior_grupo': len(comps[0]) if comps else 0,
        'densidade': (2 * m / (n * (n - 1))) if n > 1 else 0.0,
        'caminho_medio': med, 'diametro': diam,
        'dependencia_hub': dependencia,
        'grupos_sem_hub': [len(c) for c in grupos_sem_hub],
        'isolados_sem_hub': isolados_sem_hub,
        'ligacoes_entre_comunidades': entre,
        'intermediacao': sorted(((v, c) for v, c in bc.items() if c > 0), key=lambda x: -x[1])[:10],
        'grau': sorted(((v, len(adj[v])) for v in ids if adj[v]), key=lambda x: -x[1])[:10],
        'fase': f, 'fase_nome': FASES[f][0], 'fase_texto': FASES[f][1],
    }


def _comp_de(adj):
    idx = {}
    for i, c in enumerate(componentes(adj)):
        for v in c:
            idx[v] = i
    return idx


def sugerir_apresentacoes(pessoas, ligacoes, ja_feitas=(), desejos=(), hub_id=None, n=15, max_por_pessoa=2,
                          nomes_temas=None, nomes_coms=None, nomes_atu=None):
    """Pares para apresentar. ja_feitas/desejos: iteráveis de pares (a, b) de ids.
    Devolve [{'a', 'b', 'pontos', 'motivos': [...], 'temas': [...]}] ordenado por pontos."""
    nomes_temas = nomes_temas or {}
    nomes_coms = nomes_coms or {}
    nomes_atu = nomes_atu or {}
    por_id = {p['id']: p for p in pessoas}
    adj = grafo(list(por_id), ligacoes)
    comp = _comp_de(adj)
    ja = {frozenset(x) for x in ja_feitas}
    quer = {frozenset(x) for x in desejos}
    cands = []
    for a, b in combinations(sorted(por_id), 2):
        if hub_id in (a, b) or b in adj[a] or frozenset((a, b)) in ja:
            continue
        pa, pb = por_id[a], por_id[b]
        ta, tb = set(pa.get('temas') or []), set(pb.get('temas') or [])
        ca, cb = set(pa.get('comunidades') or []), set(pb.get('comunidades') or [])
        aa, ab = set(pa.get('atuacao') or []), set(pb.get('atuacao') or [])
        temas, coms = ta & tb, ca & cb
        pediu = frozenset((a, b)) in quer
        if not (temas or coms or pediu):
            continue
        pontos, motivos = 0, []
        if pediu:
            pontos += 10
            motivos.append('uma das pessoas pediu para conhecer a outra')
        if temas:
            pontos += 3 * len(temas)
            motivos.append('trabalham com ' + ', '.join(sorted(nomes_temas.get(t, t) for t in temas)))
        if coms:
            pontos += 1
            motivos.append('estão em ' + ', '.join(sorted(nomes_coms.get(c, c) for c in coms)))
        if ca and cb and ca != cb and not (ca <= cb or cb <= ca):
            pontos += 2
            motivos.append('vêm de comunidades diferentes')
        if aa and ab and not (aa & ab):
            pontos += 2
            motivos.append('atuam de lugares diferentes (' + ' × '.join(
                [', '.join(sorted(nomes_atu.get(x, x) for x in aa)), ', '.join(sorted(nomes_atu.get(x, x) for x in ab))]) + ')')
        if comp[a] != comp[b] and adj[a] and adj[b]:
            pontos += 3
            motivos.append('ligaria dois grupos que hoje não se tocam')
        if not adj[a] or not adj[b]:
            pontos += 2
            motivos.append('traz para a rede alguém que ainda não tem nenhuma ligação')
        cands.append({'a': a, 'b': b, 'pontos': pontos, 'motivos': motivos, 'temas': sorted(temas)})
    cands.sort(key=lambda c: (-c['pontos'], c['a'], c['b']))
    uso, out = {}, []
    for c in cands:
        if uso.get(c['a'], 0) >= max_por_pessoa or uso.get(c['b'], 0) >= max_por_pessoa:
            continue
        out.append(c)
        uso[c['a']] = uso.get(c['a'], 0) + 1
        uso[c['b']] = uso.get(c['b'], 0) + 1
        if len(out) >= n:
            break
    return out


def conhecer(pessoas, ligacoes, hub_id=None, n=3):
    """Sugestão pública "Pode ser bom conhecer" para cada pessoa: até n pessoas ainda não ligadas.
    Primeiro quem tem tema em comum (preferindo outra comunidade); se faltar, completa com quem está
    na mesma comunidade e é de outra organização. Usa só dados públicos e nunca sugere o hub."""
    por_id = {p['id']: p for p in pessoas}
    adj = grafo(list(por_id), ligacoes)
    out = {}
    for a, pa in por_id.items():
        ta, ca = set(pa.get('temas') or []), set(pa.get('comunidades') or [])
        org = (pa.get('organizacao') or '').strip().lower()
        por_tema, por_com = [], []
        for b, pb in por_id.items():
            if b == a or b == hub_id or b in adj[a]:
                continue
            tb, cb = set(pb.get('temas') or []), set(pb.get('comunidades') or [])
            comum = ta & tb
            if comum:
                outra = 1 if (cb - ca) else 0
                por_tema.append((-(3 * len(comum) + outra), pb['nome'], b, sorted(comum), []))
            elif ca & cb and (pb.get('organizacao') or '').strip().lower() != org:
                por_com.append((-len(ca & cb), pb['nome'], b, [], sorted(ca & cb)))
        escolhidos = sorted(por_tema)[:n]
        escolhidos += sorted(por_com)[:n - len(escolhidos)]
        out[a] = [{'id': b, 'temas': t, 'comunidades': c} for _, _, b, t, c in escolhidos]
    return out
