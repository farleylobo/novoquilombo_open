"""Monta o JSON público da RNQ a partir das três planilhas.

Função pura: recebe o que fontes.py leu e devolve (publico, avisos, interno).
- publico  -> vai para site/rnq-publico.json (só campos da lista fechada; ver config.CAMPOS_*)
- avisos   -> mensagens para o Farley (nada publicado por causa delas)
- interno  -> dados para o painel do tecelão (nunca publicados)
"""
from datetime import datetime

from . import config as C
from .rede import conhecer, metricas
from .util import chave_nome, curto, data_iso, dividir, dividir_areas, id_estavel, nao, sem_contato, sim, slug, txt


class ErroPrivacidade(Exception):
    pass


def link_seguro(url, avisos, quem):
    """Só publica links http(s); 'javascript:' ou lixo vindo da planilha viram aviso."""
    u = txt(url)
    if not u:
        return None
    if u.lower().startswith(('https://', 'http://')) and ' ' not in u:
        return u
    avisos.append(f'{quem}: LinkedIn inválido ("{u[:40]}") — não publicado')
    return None


def _lista(ordem, usados):
    vistos, out = set(), []
    for n in list(ordem) + sorted(usados):
        if n in usados and n not in vistos:
            vistos.add(n)
            out.append({'id': slug(n), 'nome': n})
    return out


class Indice:
    """Casa nomes digitados por pessoas (formulários, planilhas) com os ids do mapa."""

    def __init__(self):
        self.por_chave = {}

    def add(self, nome, pid):
        k = chave_nome(nome)
        if k:
            self.por_chave[k] = pid

    def achar(self, nome):
        k = chave_nome(nome)
        if not k:
            return None
        if k in self.por_chave:
            return self.por_chave[k]
        # nome incompleto ("Ana Souza" para "Ana Souza Lima"): só aceita se for único e tiver 2+ palavras
        if len(k.split()) >= 2:
            achados = {pid for chave, pid in self.por_chave.items() if chave.startswith(k + ' ') or chave == k}
            if len(achados) == 1:
                return achados.pop()
        return None


def montar(selecao, temas_info, tec, agora=None):
    agora = agora or datetime.now()
    avisos = []
    tec = tec or {}

    def publico_txt(v, limite, onde):
        limpo, tirou = sem_contato(v)
        if tirou:
            avisos.append(f'{onde}: e-mail/telefone removido do texto público')
        return curto(limpo, limite)

    # ---- 1. correções (sem mexer na planilha de seleção)
    corr = {}
    for r in tec.get('Correções', []):
        if not sim(r.get('Aplicar?')):
            continue
        campo = {'nome': 'nome', 'cargo': 'cargo', 'organizacao': 'organizacao', 'linkedin': 'linkedin'}.get(
            slug(r.get('Campo')).replace('-', ''))
        if campo and txt(r.get('Pessoa (nome na seleção)')):
            corr.setdefault(chave_nome(r['Pessoa (nome na seleção)']), {})[campo] = txt(r.get('Novo valor'))

    # ---- 2. saídas (RF8: prioridade; só não sai se o Farley marcou "Não")
    sair = {chave_nome(r.get('Nome')) for r in tec.get('Saídas', [])
            if txt(r.get('Nome')) and not nao(r.get('Remover?'))}

    # ---- 3. pessoas
    validas = [c for c in selecao['comunidades'] if c not in C.EXCLUIR_COMUNIDADES]
    cls = temas_info.get('por_chave', {})
    if not temas_info.get('existe'):
        avisos.append('RNQ-temas-atuacao.xlsx não encontrado: site sai sem temas e atuação')
    pessoas, idx, removidas = [], Indice(), 0
    for p in selecao['pessoas']:
        original = p['nome']
        c = corr.get(chave_nome(original), {})
        nome = c.get('nome') or original
        if chave_nome(original) in sair or chave_nome(nome) in sair:
            removidas += 1
            continue
        coms, temas_extra = [], []
        for com in p['comunidades']:
            if com in C.COMUNIDADE_PARA_TEMA:
                temas_extra.append(C.COMUNIDADE_PARA_TEMA[com])
            elif com in C.EXCLUIR_COMUNIDADES:
                continue
            elif com in validas:
                if com not in coms:
                    coms.append(com)
            else:
                avisos.append(f'{original}: comunidade "{com}" não está na aba Comunidades (ignorada)')
        temas, atu = cls.get(p['ext']) or cls.get(original) or ([], [])
        if temas_info.get('existe') and p['ext'] not in cls and original not in cls:
            avisos.append(f'{original}: não está na planilha de temas (sai sem temas e atuação)')
        todos = []
        for t in [C.RENOMEAR_TEMA.get(t, t) for t in temas] + temas_extra:
            if t in C.TEMA_PARA_COMUNIDADE:
                com = C.TEMA_PARA_COMUNIDADE[t]
                if com in validas and com not in coms:
                    coms.append(com)
            elif t not in todos:
                todos.append(t)
        if not coms:
            avisos.append(f'{nome}: sem comunidade')
        pid = slug(nome)
        if any(x['id'] == pid for x in pessoas):
            pid = f'{pid}-{slug(p["ext"])[-6:] or len(pessoas)}'
        idx.add(original, pid)
        idx.add(nome, pid)
        pessoas.append({
            'id': pid, 'nome': nome,
            'cargo': c.get('cargo', p['cargo']) or None,
            'organizacao': c.get('organizacao', p['organizacao']) or None,
            'comunidades': [slug(x) for x in coms],
            'temas': [slug(t) for t in todos],
            'atuacao': [slug(a) for a in atu],
            'linkedin': link_seguro(c.get('linkedin', p['linkedin']), avisos, nome),
            'papeis': [], 'compartilha': None, 'aprende': None, 'convoca': None, 'conhecer': [],
            '_temas': todos, '_coms': coms, '_atu': atu,
        })
    if removidas:
        avisos.append(f'{removidas} pessoa(s) removida(s) por pedido de saída (aba Saídas)')
    nomes_mapa = {chave_nome(p['nome']) for p in selecao['pessoas']} | {
        chave_nome(c['nome']) for c in corr.values() if c.get('nome')}
    for r in tec.get('Saídas', []):
        if txt(r.get('Nome')) and not nao(r.get('Remover?')) and chave_nome(r.get('Nome')) not in nomes_mapa:
            avisos.append(f'Saídas: "{txt(r.get("Nome"))}" não corresponde a ninguém do mapa — confira o nome')
    por_id = {p['id']: p for p in pessoas}

    comunidades = [{'id': slug(c), 'nome': c} for c in validas
                   if c not in C.COMUNIDADE_PARA_TEMA and any(slug(c) in p['comunidades'] for p in pessoas)]
    ordem_t = [C.RENOMEAR_TEMA.get(t, t) for t in temas_info.get('ordem_temas', [])]
    ordem_t = [t for t in ordem_t if t not in C.TEMA_PARA_COMUNIDADE] + list(C.COMUNIDADE_PARA_TEMA.values())
    temas = _lista(ordem_t, {t for p in pessoas for t in p['_temas']})
    atuacoes = _lista(temas_info.get('ordem_atuacao', []), {a for p in pessoas for a in p['_atu']})
    if not C.CONTATO_PRIVACIDADE:
        avisos.append('Sem e-mail de privacidade (rnq/config.py, CONTATO_PRIVACIDADE): preencha antes de publicar')
    for g in comunidades + temas + atuacoes:          # versão em inglês (botão PT | EN do site)
        g['nome_en'] = C.NOMES_EN.get(g['nome'])
        if not g['nome_en']:
            avisos.append(f'Sem tradução em inglês: "{g["nome"]}" (acrescente em rnq/config.py, NOMES_EN)')
    areas_validas = {chave_nome(x['nome']): x['nome'] for x in comunidades + temas}

    # ---- 4. ligações (todas passam por aprovação do Farley — RF6)
    ligs, vistas = [], set()

    def ligar(a_nome, b_nome, origem, onde):
        a, b = idx.achar(a_nome), idx.achar(b_nome)
        if not a or not b:
            falta = a_nome if not a else b_nome
            if chave_nome(falta) not in sair:
                avisos.append(f'{onde}: "{falta}" não está no mapa (ligação {a_nome} ↔ {b_nome} ignorada)')
            return
        k = frozenset((a, b))
        if a != b and k not in vistas:
            vistas.add(k)
            x, y = sorted((a, b))
            ligs.append({'a': x, 'b': y, 'origem': origem})

    for a, b in selecao['ligacoes']:
        ligar(a, b, 'curada', 'Seleção/Ligações')
    for r in tec.get('Ligações sugeridas', []):
        if sim(r.get('Aprovar?')):
            ligar(txt(r.get('Pessoa')), txt(r.get('Quem sugere')), 'sugerida', 'Ligações sugeridas')
    for r in tec.get('Apresentações', []):
        if chave_nome(r.get('Status')) in C.STATUS_APRESENTACAO_CONECTADA:
            ligar(txt(r.get('Pessoa A')), txt(r.get('Pessoa B')), 'apresentacao', 'Apresentações')

    # ---- 5. perfis (o que a própria pessoa contou; última resposta publicada vale)
    desejos = []
    for r in tec.get('Perfis', []):
        pid = idx.achar(r.get('Pessoa no mapa'))
        if not pid:
            if txt(r.get('Pessoa no mapa')):
                avisos.append(f'Perfis: "{txt(r.get("Pessoa no mapa"))}" não está no mapa')
            continue
        for nome in dividir(r.get('Gostaria de colaborar com')):
            outro = idx.achar(nome)
            if outro and outro != pid:
                desejos.append((pid, outro))
        if not sim(r.get('Publicar?')):
            continue
        p = por_id[pid]
        onde = f'Perfis ({p["nome"]})'
        p['compartilha'] = publico_txt(r.get('Posso compartilhar'), C.LIM_PERFIL, onde) or p['compartilha']
        p['aprende'] = publico_txt(r.get('Quero aprender'), C.LIM_PERFIL, onde) or p['aprende']
        p['convoca'] = publico_txt(r.get('Toparia convocar grupo sobre'), C.LIM_PERFIL, onde) or p['convoca']
        for nome in dividir(r.get('Colaboro com')):
            ligar(p['nome'], nome, 'colaboracao', f'Perfis ({p["nome"]})')

    # ---- 6. papéis
    papel_por_nome = {chave_nome(x['nome']): x['id'] for x in C.PAPEIS}
    for r in tec.get('Papéis', []):
        pid = idx.achar(r.get('Pessoa'))
        if not pid:
            if txt(r.get('Pessoa')):
                avisos.append(f'Papéis: "{txt(r.get("Pessoa"))}" não está no mapa')
            continue
        for col in ('Papel 1', 'Papel 2'):
            pp = papel_por_nome.get(chave_nome(r.get(col)))
            if pp and pp not in por_id[pid]['papeis']:
                por_id[pid]['papeis'].append(pp)

    def areas(v, onde):
        out = []
        for a in dividir_areas(v):
            nome = areas_validas.get(chave_nome(C.RENOMEAR_TEMA.get(a, a)))
            if nome and nome not in out:
                out.append(nome)
            elif not nome:
                avisos.append(f'{onde}: área "{a}" não existe (use um tema ou comunidade do mapa)')
        return out

    # ---- 7. mural
    mural = []
    for r in tec.get('Mural', []):
        if not sim(r.get('Publicar?')):
            continue
        titulo = publico_txt(r.get('Título'), C.LIM_TITULO, 'Mural')
        tipo = chave_nome(r.get('Tipo'))
        if tipo not in ('oferta', 'pedido') or not titulo:
            avisos.append(f'Mural: item "{titulo or "(sem título)"}" sem tipo (Oferta/Pedido) ou sem título — não publicado')
            continue
        autor_nome = txt(r.get('Nome'))
        autor_id = idx.achar(r.get('Está no mapa como')) or idx.achar(autor_nome)
        if chave_nome(autor_nome) in sair or chave_nome(r.get('Está no mapa como')) in sair:
            continue
        mural.append({
            'id': txt(r.get('ID')) or id_estavel('m', titulo, autor_nome),
            'tipo': tipo, 'titulo': titulo, 'descricao': publico_txt(r.get('Descrição'), C.LIM_TEXTO, f'Mural "{titulo}"'),
            'areas': areas(r.get('Áreas'), f'Mural "{titulo}"'),
            'autor': (por_id[autor_id]['nome'] if autor_id else curto(autor_nome, 60)) or None,
            'autor_id': autor_id, 'data': data_iso(r.get('Recebido em')) or agora.strftime('%Y-%m-%d'),
            'status': 'atendido' if chave_nome(r.get('Status')) == 'atendido' else 'aberto',
        })
    mural.sort(key=lambda m: m['data'], reverse=True)
    mural.sort(key=lambda m: m['status'] != 'aberto')

    # ---- 8. iniciativas
    iniciativas = []
    for r in tec.get('Iniciativas', []):
        if not sim(r.get('Publicar?')):
            continue
        titulo = publico_txt(r.get('Título'), C.LIM_TITULO, 'Iniciativas')
        if not titulo:
            continue
        tipo = txt(r.get('Tipo'))
        tipo = tipo if tipo in C.TIPOS_INICIATIVA else 'Projeto'
        part = []
        for nome in dividir(r.get('Participantes')):
            pid = idx.achar(nome)
            if pid and pid not in part:
                part.append(pid)
            elif not pid and chave_nome(nome) not in sair:
                avisos.append(f'Iniciativa "{titulo}": participante "{nome}" não está no mapa (não exibido)')
        prop_nome = txt(r.get('Nome de quem propôs'))
        prop_id = idx.achar(prop_nome)
        if chave_nome(prop_nome) in sair:
            continue
        iniciativas.append({
            'id': txt(r.get('ID')) or id_estavel('i', titulo, prop_nome),
            'tipo': tipo, 'titulo': titulo,
            'descricao': publico_txt(r.get('Descrição'), C.LIM_TEXTO, f'Iniciativa "{titulo}"'),
            'areas': areas(r.get('Áreas'), f'Iniciativa "{titulo}"'),
            'participantes': part,
            'precisa': publico_txt(r.get('Precisa de'), C.LIM_PERFIL, f'Iniciativa "{titulo}"') or None,
            'proponente': (por_id[prop_id]['nome'] if prop_id else curto(prop_nome, 60)) or None,
            'proponente_id': prop_id, 'data': data_iso(r.get('Recebido em')) or agora.strftime('%Y-%m-%d'),
            'status': 'concluida' if chave_nome(r.get('Status')) in ('concluida',) else 'ativa',
        })
    iniciativas.sort(key=lambda i: (i['status'] != 'ativa', i['data']))

    # ---- 9. sugestões públicas e estatísticas
    hub = idx.achar(C.HUB_NOME)
    pares = [(l['a'], l['b']) for l in ligs]
    for pid, lst in conhecer(pessoas, pares, hub_id=hub).items():
        por_id[pid]['conhecer'] = lst
    met = metricas(pessoas, pares, hub_id=hub)
    estat = {
        'pessoas': len(pessoas), 'ligacoes': len(ligs),
        'organizacoes': len({chave_nome(p['organizacao']) for p in pessoas if p['organizacao']}),
        'comunidades': len(comunidades), 'temas': len(temas),
        'pct_conectadas': round(met['pct_conectadas'] * 100),
        'mural_abertos': sum(1 for m in mural if m['status'] == 'aberto'),
        'iniciativas_ativas': sum(1 for i in iniciativas if i['status'] == 'ativa'),
    }

    for p in pessoas:
        for k in ('_temas', '_coms', '_atu'):
            p.pop(k)
    publico = {
        'versao': 3, 'gerado_em': agora.strftime('%Y-%m-%d %H:%M'),
        'comunidades': comunidades, 'temas': temas, 'atuacoes': atuacoes,
        'papeis': [dict(x) for x in C.PAPEIS],
        'pessoas': pessoas, 'ligacoes': ligs, 'mural': mural, 'iniciativas': iniciativas,
        'estatisticas': estat,
        'sobre': {'responsavel': C.RESPONSAVEL_DADOS, 'contato': C.CONTATO_PRIVACIDADE or None},
    }
    validar(publico, tec)
    ja = [(idx.achar(r.get('Pessoa A')), idx.achar(r.get('Pessoa B'))) for r in tec.get('Apresentações', [])]
    interno = {'indice': idx, 'hub': hub, 'metricas': met, 'desejos': desejos,
               'ja_apresentadas': [x for x in ja if all(x)]}
    return publico, avisos, interno


def validar(publico, tec=None):
    """CA1 + privacidade: só campos da lista fechada; nenhum contato privado no JSON."""
    def checar(obj, permitidos, onde):
        extra = set(obj) - permitidos
        if extra:
            raise ErroPrivacidade(f'{onde}: campo não público {sorted(extra)}')
    checar(publico, C.CAMPOS_TOPO, 'topo')
    for p in publico['pessoas']:
        checar(p, C.CAMPOS_PESSOA, f'pessoa {p.get("nome")}')
    for m in publico['mural']:
        checar(m, C.CAMPOS_MURAL, f'mural {m.get("titulo")}')
    for i in publico['iniciativas']:
        checar(i, C.CAMPOS_INICIATIVA, f'iniciativa {i.get("titulo")}')
    for l in publico['ligacoes']:
        checar(l, C.CAMPOS_LIGACAO, 'ligação')
    for k in ('comunidades', 'temas', 'atuacoes'):
        for g in publico.get(k, []):
            checar(g, C.CAMPOS_GRUPO, f'{k} {g.get("nome")}')
    for x in publico.get('papeis', []):
        checar(x, C.CAMPOS_PAPEL, f'papel {x.get("nome")}')
    if 'sobre' in publico:
        checar(publico['sobre'], C.CAMPOS_SOBRE, 'sobre')
    if tec:
        import json
        texto = json.dumps(publico, ensure_ascii=False).lower()
        for aba, linhas in tec.items():
            for r in linhas:
                for col, v in r.items():
                    privado = 'privado' in col.lower()
                    interno = col.lower().startswith('observação')
                    if privado or interno:
                        s = txt(v).lower()
                        if len(s) >= (6 if privado else 16) and s in texto:
                            raise ErroPrivacidade(f'{aba}/{col}: conteúdo privado apareceria no site')
    return True
