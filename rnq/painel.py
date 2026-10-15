"""Painel do tecelão: HTML local, só para quem tece a rede. NUNCA publicar (tem contatos privados).

Responde, numa página:
1. Em que fase a rede está (Holley/Krebs) e o quanto ela depende de você.
2. Quem apresentar a quem esta semana — com motivo e mensagem pronta.
3. O que está esperando sua moderação.
4. Quais pedidos do mural ainda não têm ninguém, e quem no mapa pode ajudar.

Idiomas: gerar(..., idioma='pt' | 'en'). Os textos do painel ficam em TEXTOS (os dois blocos têm as mesmas
chaves; um teste confere). Nomes de temas, comunidades e atuação usam nome_en quando existe. O que as
pessoas escrevem (mural, mensagens) e os nomes de abas e colunas da planilha ficam como estão, em português,
porque é assim que aparecem no Excel.
"""
import html
from datetime import datetime

from . import config as C
from .rede import FASES, FASES_EN
from .util import chave_nome, nao, sim, txt

IDIOMAS = ('pt', 'en')

TEXTOS = {
    'pt': {
        'lang': 'pt-BR',
        'titulo_pagina': 'Painel do tecelão · RNQ',
        'titulo': 'Painel do tecelão',
        'rede': 'Rede Novo Quilombo',
        'gerado': 'gerado em',
        'formato_data': '%d/%m/%Y %H:%M',
        'privado': 'Documento interno: tem contatos privados. Não publique nem compartilhe este arquivo.',
        'privado_painel': 'Área restrita: tem contatos privados. Não copie nem repasse para fora da equipe de tecelagem.',
        'escopo_rede': 'Rede toda',
        'outro_idioma': '<a href="painel-tecelagem-en.html">English version</a>',
        'nota_planilha': '',
        'saude': 'Saúde da rede',
        'dep_hub': lambda pct, quem: f'{pct} das ligações passam por {quem}.',
        'hub_fora': 'O hub configurado não está no mapa.',
        'hub_fora_escopo': 'O hub da rede não está nesta comunidade: aqui as ligações não dependem dele.',
        'sem_hub': lambda quem, g, i: f'Sem {quem}, a rede viraria {g} grupo(s) e {i} pessoa(s) ficariam isoladas.',
        'kpi_conectadas': 'Pessoas conectadas', 'kpi_conectadas_sub': lambda p: f'{p} da rede',
        'kpi_ligacoes': 'Ligações', 'kpi_ligacoes_sub': lambda n: f'{n} entre comunidades diferentes',
        'kpi_grupos': 'Grupos separados', 'kpi_grupos_sub': lambda n: f'maior grupo: {n} pessoas',
        'kpi_caminho': 'Caminho médio', 'kpi_caminho_sub': lambda d: f'passos entre duas pessoas (máx. {d})',
        'kpi_dep': 'Dependência do hub', 'kpi_dep_sub': 'meta: abaixo de 30%',
        'evolucao': 'Evolução', 'evolucao_sub': '% de pessoas conectadas ao longo das atualizações',
        'col_data': 'Data', 'col_pessoas': 'Pessoas', 'col_ligacoes': 'Ligações', 'col_conectadas': 'Conectadas',
        'col_dep': 'Dep. hub', 'col_fase': 'Fase',
        'esperando': 'Esperando você',
        'pend': ['itens esperando "Publicar?"', '"posso ajudar" sem apresentação feita', 'perfis esperando "Publicar?"',
                 'ligações esperando "Aprovar?"', 'iniciativas esperando "Publicar?"',
                 'pedidos de participação não encaminhados', 'cadastros do "Faça parte" esperando "Incluir no mapa?"',
                 'pedidos de saída (já aplicados)'],
        'aba': 'aba',
        'esperando_rodape': 'Tudo isso fica na planilha RNQ-tecelagem.xlsx.',
        'esperando_rodape_painel': ('Aprove ou recuse na aba Moderação deste painel. Os números são da última '
                                    'atualização feita no Mac (python3 atualizar.py).'),
        'sugeridas': 'Apresentações sugeridas',
        'sugeridas_sub': ('Critério (June Holley): tema em comum para gerar confiança, comunidade ou atuação diferente '
                          'para trazer novidade.\nPares que unem grupos separados ou trazem alguém isolado valem mais. '
                          'Você nunca aparece aqui: a ideia é a rede depender menos de você.\nO impacto acontece quando '
                          'você apresenta <b>e acompanha</b> — e melhor ainda se já sugerir algo concreto para fazerem juntos.'),
        'copiar': 'Copiar mensagem', 'copiado': 'Copiado',
        'registre': lambda a, b: (f'Depois de apresentar, registre na aba Apresentações: Pessoa A = {a}, '
                                  f'Pessoa B = {b}, Status = Apresentadas.'),
        'sem_sugestoes': 'Sem sugestões novas: todo par com tema em comum já está ligado ou registrado.',
        'motivo_temas': lambda nomes: 'vocês dois trabalham com ' + ' e '.join(nomes),
        'motivo_padrao': 'vocês têm muito em comum',
        'msg_apresentacao': lambda a, b, qa, qb, motivo: (
            f'Oi {a} e {b}! Quero apresentar vocês. {qa} e {qb}. Acho que vale uma conversa porque {motivo}. '
            f'Topam um papo de 30 minutos? Me contem depois como foi. — Rede Novo Quilombo'),
        'razao': {
            'pediu': lambda r, n: 'uma das pessoas pediu para conhecer a outra',
            'temas': lambda r, n: 'trabalham com ' + ', '.join(sorted(n['tema'](x) for x in r['ids'])),
            'comunidades': lambda r, n: 'estão em ' + ', '.join(sorted(n['com'](x) for x in r['ids'])),
            'comunidades_diferentes': lambda r, n: 'vêm de comunidades diferentes',
            'atuacoes_diferentes': lambda r, n: 'atuam de lugares diferentes (' + ' × '.join(
                ', '.join(sorted(n['atu'](x) for x in r[k])) for k in ('a', 'b')) + ')',
            'ponte': lambda r, n: 'ligaria dois grupos que hoje não se tocam',
            'isolado': lambda r, n: 'traz para a rede alguém que ainda não tem nenhuma ligação',
        },
        'ligacoes_n': lambda g: f'{g} ligação' if g == 1 else f'{g} ligações',
        'funil': 'Funil de apresentações',
        'status': {s: s for s in C.STATUS_APRESENTACAO},
        'funil_sub': ('Registre cada apresentação na aba Apresentações. "Apresentadas", "Acompanhando" e '
                      '"Colaborando" viram ligação no mapa.'),
        'posso_ajudar': '"Posso ajudar" esperando apresentação',
        'quem_publicou': 'quem publicou', 'alguem': 'alguém',
        'msg_resposta': lambda autor, quem, titulo, extra: (
            f'Oi {autor} e {quem}! Quero apresentar vocês. {quem} respondeu ao "{titulo}" no mural da Rede Novo '
            f'Quilombo{": " + extra if extra else ""}. Combinem um papo e me contem como foi!'),
        'sobre': 'sobre', 'contatos': 'Contatos', 'sem_contato': 'sem contato',
        'marque_feita': 'Depois marque "Apresentação feita? = Sim" na aba Respostas do mural.',
        'marque_feita_painel': 'Depois marque como feita na aba Moderação deste painel.',
        'nenhuma_resposta': 'Nenhuma resposta esperando.',
        'pedidos': 'Pedidos do mural em aberto',
        'de': 'de', 'contato': 'contato',
        'ja_respondido': 'Já recebeu resposta. ', 'ninguem_respondeu': 'Ninguém respondeu ainda. ',
        'quem_trabalha': 'Quem no mapa trabalha com isso', 'ninguem_ainda': 'ninguém ainda',
        'nenhum_pedido': 'Nenhum pedido aberto no mural.',
        'antigos': 'Itens antigos no mural',
        'antigos_dias': lambda d: f'{d} dias',
        'antigos_sub': ('Abertos há mais de 45 dias. Pergunte a quem publicou se ainda vale; '
                        'se não, marque "Status = Atendido".'),
        'nenhum_antigo': 'Nenhum item aberto há mais de 45 dias.',
        'semana': 'Mensagem da semana para os grupos',
        'semana_sub': 'Pronta para colar no WhatsApp: novidades dos últimos 7 dias e um convite para participar.',
        'pontes': 'Pontes',
        'pontes_sub': 'Quem mais está no caminho entre os outros (intermediação). Boas candidatas a tecer junto com você.',
        'mais_conectadas': 'Mais conectadas',
        'isolados': lambda n: f'Ainda sem nenhuma ligação ({n})', 'ninguem': 'Ninguém.',
        'avisos': 'Avisos da última atualização', 'nenhum_aviso': 'Nenhum aviso.',
        # mensagem da semana
        'sem_link': '<link do mapa>',
        'sem_titulo': '*Rede Novo Quilombo — novidades da semana*',
        'sem_somos': lambda p, o, c: f'Somos {p} pessoas, de {o} organizações, em {c} comunidades.',
        'sem_pedidos': '*Pedidos — alguém pode ajudar?*', 'sem_ofertas': '*Ofertas*',
        'sem_inis': '*Iniciativas novas*',
        'sem_vazio': 'O mural está esperando você: o que você pode oferecer à rede? O que está precisando?',
        'sem_convite': lambda link: f'Veja o mapa, publique no mural ou apresente alguém: {link}#mural',
        'sem_perfil': 'Está no mapa e quer atualizar seu perfil ou sair? Busque seu nome e abra seu card.',
    },
    'en': {
        'lang': 'en',
        'titulo_pagina': "Weaver's panel · Novo Quilombo Network",
        'titulo': "Weaver's panel",
        'rede': 'Novo Quilombo Network',
        'gerado': 'generated',
        'formato_data': '%Y-%m-%d %H:%M',
        'privado': 'Internal document: it holds private contacts. Do not publish or share this file.',
        'privado_painel': 'Restricted area: it holds private contacts. Do not copy or pass them on outside the weaving team.',
        'escopo_rede': 'Whole network',
        'outro_idioma': '<a href="painel-tecelagem.html">Versão em português</a>',
        'nota_planilha': ('<p class="muted">Tab and column names from the RNQ-tecelagem.xlsx spreadsheet, and what '
                          'people wrote, are shown as they are, in Portuguese.</p>'),
        'saude': 'Network health',
        'dep_hub': lambda pct, quem: f'{pct} of links go through {quem}.',
        'hub_fora': 'The configured hub is not on the map.',
        'hub_fora_escopo': 'The network hub is not in this community: links here do not depend on them.',
        'sem_hub': lambda quem, g, i: (f'Without {quem}, the network would split into {g} group(s) and '
                                       f'{i} person(s) would be isolated.'),
        'kpi_conectadas': 'People connected', 'kpi_conectadas_sub': lambda p: f'{p} of the network',
        'kpi_ligacoes': 'Links', 'kpi_ligacoes_sub': lambda n: f'{n} across different communities',
        'kpi_grupos': 'Separate groups', 'kpi_grupos_sub': lambda n: f'largest group: {n} people',
        'kpi_caminho': 'Average path', 'kpi_caminho_sub': lambda d: f'steps between two people (max {d})',
        'kpi_dep': 'Hub dependence', 'kpi_dep_sub': 'goal: below 30%',
        'evolucao': 'Evolution', 'evolucao_sub': '% of people connected over updates',
        'col_data': 'Date', 'col_pessoas': 'People', 'col_ligacoes': 'Links', 'col_conectadas': 'Connected',
        'col_dep': 'Hub dep.', 'col_fase': 'Phase',
        'esperando': 'Waiting for you',
        'pend': ['items waiting for "Publicar?"', '"I can help" replies without an introduction yet',
                 'profiles waiting for "Publicar?"', 'links waiting for "Aprovar?"',
                 'initiatives waiting for "Publicar?"', 'participation requests not forwarded',
                 '"Join" sign-ups waiting for "Incluir no mapa?"', 'removal requests (already applied)'],
        'aba': 'tab',
        'esperando_rodape': 'All of this lives in the RNQ-tecelagem.xlsx spreadsheet.',
        'esperando_rodape_painel': ('Approve or decline in the Moderation tab of this panel. Numbers come from the '
                                    'last update run on the Mac (python3 atualizar.py).'),
        'sugeridas': 'Suggested introductions',
        'sugeridas_sub': ('Criterion (June Holley): a shared theme builds trust; a different community or role brings '
                          'novelty.\nPairs that join separate groups or bring in someone isolated score higher. '
                          'You never appear here: the goal is for the network to depend less on you.\nImpact happens '
                          'when you introduce <b>and follow up</b>, even better if you suggest something concrete '
                          'to do together.'),
        'copiar': 'Copy message', 'copiado': 'Copied',
        'registre': lambda a, b: (f'After introducing, log it in the Apresentações tab: Pessoa A = {a}, '
                                  f'Pessoa B = {b}, Status = Apresentadas.'),
        'sem_sugestoes': 'No new suggestions: every pair with a theme in common is already linked or logged.',
        'motivo_temas': lambda nomes: 'you both work on ' + ' and '.join(nomes),
        'motivo_padrao': 'you have a lot in common',
        'msg_apresentacao': lambda a, b, qa, qb, motivo: (
            f"Hi {a} and {b}! I'd like to introduce you. {qa} and {qb}. I think a conversation is worth it because "
            f'{motivo}. Up for a 30-minute chat? Let me know how it went. — Novo Quilombo Network'),
        'razao': {
            'pediu': lambda r, n: 'one of them asked to meet the other',
            'temas': lambda r, n: 'both work on ' + ', '.join(sorted(n['tema'](x) for x in r['ids'])),
            'comunidades': lambda r, n: 'both in ' + ', '.join(sorted(n['com'](x) for x in r['ids'])),
            'comunidades_diferentes': lambda r, n: 'come from different communities',
            'atuacoes_diferentes': lambda r, n: 'act from different places (' + ' × '.join(
                ', '.join(sorted(n['atu'](x) for x in r[k])) for k in ('a', 'b')) + ')',
            'ponte': lambda r, n: 'would link two groups that do not touch today',
            'isolado': lambda r, n: 'brings in someone who has no links yet',
        },
        'ligacoes_n': lambda g: f'{g} link' if g == 1 else f'{g} links',
        'funil': 'Introductions funnel',
        'status': {'Sugerida': 'Suggested', 'Apresentadas': 'Introduced', 'Acompanhando': 'Following up',
                   'Colaborando': 'Collaborating', 'Não rolou': "Didn't happen"},
        'funil_sub': ('Log each introduction in the Apresentações tab. "Apresentadas" (introduced), "Acompanhando" '
                      '(following up) and "Colaborando" (collaborating) become links on the map.'),
        'posso_ajudar': '"I can help" replies waiting for an introduction',
        'quem_publicou': 'the author', 'alguem': 'someone',
        'msg_resposta': lambda autor, quem, titulo, extra: (
            f"Hi {autor} and {quem}! I'd like to introduce you. {quem} replied to \"{titulo}\" on the Novo Quilombo "
            f'Network board{": " + extra if extra else ""}. Set up a chat and let me know how it went!'),
        'sobre': 'about', 'contatos': 'Contacts', 'sem_contato': 'no contact',
        'marque_feita': 'Then set "Apresentação feita? = Sim" in the Respostas do mural tab.',
        'marque_feita_painel': 'Then mark it as done in the Moderation tab of this panel.',
        'nenhuma_resposta': 'No replies waiting.',
        'pedidos': 'Open requests on the board',
        'de': 'by', 'contato': 'contact',
        'ja_respondido': 'Already has a reply. ', 'ninguem_respondeu': 'No one has replied yet. ',
        'quem_trabalha': 'Who on the map works on this', 'ninguem_ainda': 'no one yet',
        'nenhum_pedido': 'No open requests on the board.',
        'antigos': 'Old items on the board',
        'antigos_dias': lambda d: f'{d} days',
        'antigos_sub': ('Open for more than 45 days. Ask the author if it still matters; '
                        'if not, set "Status = Atendido".'),
        'nenhum_antigo': 'No item open for more than 45 days.',
        'semana': 'Message of the week for the groups',
        'semana_sub': 'Ready to paste into WhatsApp: news from the last 7 days and an invitation to take part.',
        'pontes': 'Bridges',
        'pontes_sub': 'Who sits most often on the path between others (betweenness). Good candidates to weave with you.',
        'mais_conectadas': 'Most connected',
        'isolados': lambda n: f'No links yet ({n})', 'ninguem': 'No one.',
        'avisos': 'Warnings from the last update', 'nenhum_aviso': 'No warnings.',
        # message of the week
        'sem_link': '<map link>',
        'sem_titulo': '*Novo Quilombo Network — news of the week*',
        'sem_somos': lambda p, o, c: f'We are {p} people, from {o} organizations, in {c} communities.',
        'sem_pedidos': '*Requests — can anyone help?*', 'sem_ofertas': '*Offers*',
        'sem_inis': '*New initiatives*',
        'sem_vazio': 'The board is waiting for you: what can you offer the network? What do you need?',
        'sem_convite': lambda link: f'See the map, post on the board or introduce someone: {link}#mural',
        'sem_perfil': 'On the map and want to update your profile or leave? Search your name and open your card.',
    },
}


def _t(idioma):
    if idioma not in TEXTOS:
        raise ValueError(f'idioma desconhecido: {idioma!r} (use {", ".join(IDIOMAS)})')
    return TEXTOS[idioma]


def _e(s):
    return html.escape(txt(s))


def _pct(x):
    return f'{round(x * 100)}%'


def _primeiro(nome):
    return txt(nome).split(' ')[0] if nome else ''


def _botao(T, painel):
    if painel:
        return f'<button type="button" data-copiar data-copiado="{_e(T["copiado"])}">{_e(T["copiar"])}</button>'
    return f'<button onclick="copiar(this)">{T["copiar"]}</button>'


def _script_arquivo(T):
    return (f"function copiar(b){{const t=b.previousElementSibling;t.select();navigator.clipboard?.writeText(t.value);"
            f"b.textContent='{T['copiado']}';setTimeout(()=>b.textContent='{T['copiar']}',1500)}}")


def mensagem_apresentacao(pa, pb, motivo, idioma='pt'):
    def quem(p):
        cargo, org = txt(p.get('cargo')), txt(p.get('organizacao'))
        partes = [x for x in (cargo, org if org.lower() not in cargo.lower() else '') if x]
        return f'{p["nome"]}' + (f' ({", ".join(partes)})' if partes else '')
    return _t(idioma)['msg_apresentacao'](_primeiro(pa['nome']), _primeiro(pb['nome']), quem(pa), quem(pb), motivo)


def _sparkline(valores, largura=220, altura=40):
    if len(valores) < 2:
        return ''
    mx, mn = max(valores), min(valores)
    faixa = (mx - mn) or 1
    pts = ' '.join(f'{i * largura / (len(valores) - 1):.1f},{altura - 4 - (v - mn) / faixa * (altura - 8):.1f}'
                   for i, v in enumerate(valores))
    return (f'<svg width="{largura}" height="{altura}" viewBox="0 0 {largura} {altura}" aria-hidden="true">'
            f'<polyline points="{pts}" fill="none" stroke="currentColor" stroke-width="2"/></svg>')


def pendencias(tec, idioma='pt'):
    def contar(aba, col, cond):
        return sum(1 for r in tec.get(aba, []) if cond(r.get(col)))
    vazio = lambda v: not txt(v)
    nao_sim = lambda v: not sim(v)
    d = _t(idioma)['pend']
    return [
        ('Mural', d[0], contar('Mural', 'Publicar?', vazio)),
        ('Respostas do mural', d[1], contar('Respostas do mural', 'Apresentação feita?', nao_sim)),
        ('Perfis', d[2], contar('Perfis', 'Publicar?', vazio)),
        ('Ligações sugeridas', d[3], contar('Ligações sugeridas', 'Aprovar?', vazio)),
        ('Iniciativas', d[4], contar('Iniciativas', 'Publicar?', vazio)),
        ('Participações', d[5], contar('Participações', 'Encaminhado?', nao_sim)),
        ('Cadastros', d[6], contar('Cadastros', 'Incluir no mapa?', vazio)),
        ('Saídas', d[7], contar('Saídas', 'Remover?', lambda v: not nao(v))),
    ]


def _dias(data_iso, agora):
    try:
        return (agora.date() - datetime.strptime(data_iso, '%Y-%m-%d').date()).days
    except (TypeError, ValueError):
        return 0


def mensagem_semana(publico, agora, site_url='', idioma='pt'):
    """Texto pronto para colar nos grupos de WhatsApp: novidades dos últimos 7 dias + convite."""
    T = _t(idioma)
    link = site_url.rstrip('/') if site_url else T['sem_link']
    novos = [m for m in publico['mural'] if m['status'] == 'aberto' and _dias(m['data'], agora) <= 7]
    inis = [i for i in publico['iniciativas'] if i['status'] == 'ativa' and _dias(i['data'], agora) <= 7]
    e = publico['estatisticas']
    linhas = [T['sem_titulo'], '', T['sem_somos'](e['pessoas'], e['organizacoes'], e['comunidades'])]
    pedidos = [m for m in novos if m['tipo'] == 'pedido']
    ofertas = [m for m in novos if m['tipo'] == 'oferta']
    if pedidos:
        linhas += ['', T['sem_pedidos']] + [f'• {m["titulo"]} ({m["autor"]})' for m in pedidos[:5]]
    if ofertas:
        linhas += ['', T['sem_ofertas']] + [f'• {m["titulo"]} ({m["autor"]})' for m in ofertas[:5]]
    if inis:
        linhas += ['', T['sem_inis']] + [f'• {i["tipo"]}: {i["titulo"]}' for i in inis[:5]]
    if not (pedidos or ofertas or inis):
        linhas += ['', T['sem_vazio']]
    linhas += ['', T['sem_convite'](link), T['sem_perfil']]
    return '\n'.join(linhas)


def _nomeador(itens, idioma):
    """id -> nome no idioma (nome_en quando existe e o idioma é EN; senão o nome em português)."""
    nomes = {x['id']: (x.get('nome_en') if idioma == 'en' and x.get('nome_en') else x['nome']) for x in itens}
    return lambda i: nomes.get(i, i)


def _motivos(s, idioma, n):
    """Motivos de uma sugestão no idioma pedido. Sem 'razoes' (formato antigo), usa o texto em português."""
    if 'razoes' not in s or idioma == 'pt' and s.get('motivos'):
        return s.get('motivos') or []
    rz = _t(idioma)['razao']
    return [rz[r['tipo']](r, n) for r in s['razoes'] if r.get('tipo') in rz]


# Script do painel admin (modo='painel'): fixo, para caber numa Content-Security-Policy com hash (sem 'unsafe-inline').
# Copiar e ajustar a altura passam pela página de fora (postMessage): o iframe fica isolado, sem acesso à sessão.
SCRIPT_PAINEL = ("document.addEventListener('click',function(e){var b=e.target.closest('[data-copiar]');if(!b)return;"
                 "var t=b.previousElementSibling;parent.postMessage({rnqCopiar:t.value},'*');var o=b.textContent;"
                 "b.textContent=b.getAttribute('data-copiado');setTimeout(function(){b.textContent=o},1500)});"
                 "function rnqAltura(){parent.postMessage({rnqAltura:document.documentElement.scrollHeight},'*')}"
                 "new ResizeObserver(rnqAltura).observe(document.body);addEventListener('load',rnqAltura);")
MODOS = ('arquivo', 'painel')
# No painel admin, o conteúdo usa a mesma paleta do app (lápis-lazúli, ouro, papiro) e não repete o título.
ESTILO_PAINEL = ('<style>:root{--bg:#F1E8D4;--panel:#FBF8F1;--ink:#1F1A2B;--muted:#625A6C;--line:#DCCFB3;'
                 '--accent:#233E8B;--ok:#2F6B55}body{background:#FBF8F1}main{max-width:none;padding:16px 16px 32px}'
                 '.top h1{display:none}.priv{background:#F4E6C4;color:#5C4313}.fases li.on{background:#233E8B;'
                 'border-color:#233E8B}h2{color:#172A63}</style>')


def gerar(publico, interno, tec, sugestoes, avisos, historico=None, agora=None, site_url='', idioma='pt',
          modo='arquivo', escopo_nome=None):
    """modo='arquivo': o HTML local de sempre (painel/painel-tecelagem*.html).
    modo='painel': o mesmo conteúdo para o painel admin com login (dentro de um iframe isolado): sem links para
    arquivos locais, textos que apontam para a aba Moderação e script fixo. avisos=None esconde a seção de avisos
    (recorte de comunidade: os avisos do pipeline citam pessoas de outras comunidades)."""
    if modo not in MODOS:
        raise ValueError(f'modo desconhecido: {modo!r}')
    painel = modo == 'painel'
    T = _t(idioma)
    fases = FASES_EN if idioma == 'en' else FASES
    agora = agora or datetime.now()
    met = interno['metricas']
    por_id = {p['id']: p for p in publico['pessoas']}
    nome = lambda i: por_id[i]['nome'] if i in por_id else i
    tn = {t['id']: t['nome'] for t in publico['temas']}
    cn = {c['id']: c['nome'] for c in publico['comunidades']}
    n = {'tema': _nomeador(publico['temas'], idioma), 'com': _nomeador(publico['comunidades'], idioma),
         'atu': _nomeador(publico.get('atuacoes', []), idioma)}
    hub = interno.get('hub')
    historico = historico or []

    # ---- saúde
    trilha = ''.join(f'<li class="{"on" if f == met["fase"] else ""}">{_e(fases[f][0])}</li>'
                     for f in ('fragmentos', 'hub', 'multi-hub', 'nucleo'))
    fase_nome, fase_texto = fases.get(met['fase'], (met['fase_nome'], met['fase_texto']))
    dep_txt = T['dep_hub'](_pct(met['dependencia_hub']), _e(nome(hub))) if hub else T['hub_fora_escopo' if interno.get('recorte') else 'hub_fora']
    sem_hub = T['sem_hub'](_e(_primeiro(nome(hub))), len(met['grupos_sem_hub']), met['isolados_sem_hub']) if hub else ''
    cards = [
        (T['kpi_conectadas'], f'{met["conectadas"]}/{met["pessoas"]}', T['kpi_conectadas_sub'](_pct(met['pct_conectadas']))),
        (T['kpi_ligacoes'], met['ligacoes'], T['kpi_ligacoes_sub'](met['ligacoes_entre_comunidades'])),
        (T['kpi_grupos'], len(met['grupos']), T['kpi_grupos_sub'](met['maior_grupo'])),
        (T['kpi_caminho'], f'{met["caminho_medio"]:.1f}', T['kpi_caminho_sub'](met['diametro'])),
        (T['kpi_dep'], _pct(met['dependencia_hub']), T['kpi_dep_sub']),
    ]
    cards_html = ''.join(f'<div class="kpi"><span>{_e(t)}</span><b>{_e(v)}</b><small>{_e(s)}</small></div>'
                         for t, v, s in cards)

    hist_html = ''
    if historico:
        serie = [h.get('pct_conectadas', 0) for h in historico]
        linhas = ''.join(
            f'<tr><td>{_e(h["data"])}</td><td>{h["pessoas"]}</td><td>{h["ligacoes"]}</td>'
            f'<td>{round(h["pct_conectadas"] * 100)}%</td><td>{round(h["dependencia_hub"] * 100)}%</td>'
            f'<td>{_e(fases[h["fase"]][0] if h.get("fase") in fases else h.get("fase_nome"))}</td></tr>'
            for h in historico[-12:][::-1])
        hist_html = (f'<section><h2>{T["evolucao"]}</h2><p class="muted">{T["evolucao_sub"]} '
                     f'<span class="spark">{_sparkline(serie)}</span></p><table><thead><tr><th>{T["col_data"]}</th>'
                     f'<th>{T["col_pessoas"]}</th><th>{T["col_ligacoes"]}</th><th>{T["col_conectadas"]}</th>'
                     f'<th>{T["col_dep"]}</th><th>{T["col_fase"]}</th></tr></thead>'
                     f'<tbody>{linhas}</tbody></table></section>')

    # ---- sugestões
    sug_html = ''
    for i, s in enumerate(sugestoes, 1):
        pa, pb = por_id[s['a']], por_id[s['b']]
        motivos = _motivos(s, idioma, n)
        if s.get('temas'):
            motivo = T['motivo_temas']([n['tema'](t) for t in s['temas'][:2]])
        else:
            motivo = motivos[0] if motivos else T['motivo_padrao']
        msg = mensagem_apresentacao(pa, pb, motivo, idioma)
        sug_html += (
            f'<article class="sug"><header><b>{i}. {_e(pa["nome"])} ↔ {_e(pb["nome"])}</b>'
            f'<span class="pts">{s["pontos"]} pts</span></header>'
            f'<ul>{"".join(f"<li>{_e(m)}</li>" for m in motivos)}</ul>'
            f'<textarea readonly rows="3">{_e(msg)}</textarea>'
            f'{_botao(T, painel)}'
            f'<small class="muted">{T["registre"](_e(pa["nome"]), _e(pb["nome"]))}</small></article>')
    if not sug_html:
        sug_html = f'<p class="muted">{T["sem_sugestoes"]}</p>'

    # ---- pontes / conectores
    ponte = ''.join(f'<li>{_e(nome(v))} <small>{c:.2f}</small></li>' for v, c in met['intermediacao'][:8])
    graus = ''.join(f'<li>{_e(nome(v))} <small>{T["ligacoes_n"](g)}</small></li>' for v, g in met['grau'][:8])
    isol = ', '.join(_e(nome(v)) for v in sorted(met['isolados'], key=nome))

    # ---- pendências
    pend = ''.join(f'<li class="{"alerta" if q else ""}"><b>{q}</b> {_e(desc)} <small>{T["aba"]} {_e(aba)}</small></li>'
                   for aba, desc, q in pendencias(tec, idioma))

    # ---- funil de apresentações
    funil = {s: 0 for s in C.STATUS_APRESENTACAO}
    for r in tec.get('Apresentações', []):
        st = next((s for s in C.STATUS_APRESENTACAO if chave_nome(s) == chave_nome(r.get('Status'))), None)
        if st:
            funil[st] += 1
    funil_html = ''.join(f'<div class="etapa"><b>{q}</b><span>{_e(T["status"].get(s, s))}</span></div>'
                         for s, q in funil.items())

    # ---- pedidos do mural sem resposta
    respondidos = {txt(r.get('ID do item')) for r in tec.get('Respostas do mural', [])}
    contatos = {txt(r.get('ID')): txt(r.get('Contato (privado)')) for r in tec.get('Mural', [])}
    ped_html = ''
    for m in publico['mural']:
        if m['tipo'] != 'pedido' or m['status'] != 'aberto':
            continue
        areas = {chave_nome(a) for a in m['areas']}
        quem = [p for p in publico['pessoas'] if p['id'] != m['autor_id'] and (
            {chave_nome(tn.get(t, '')) for t in p['temas']} | {chave_nome(cn.get(c, '')) for c in p['comunidades']}) & areas]
        ped_html += (f'<article class="ped"><b>{_e(m["titulo"])}</b> <small>{T["de"]} {_e(m["autor"])} · {_e(m["data"])}'
                     f'{" · " + T["contato"] + ": " + _e(contatos.get(m["id"])) if contatos.get(m["id"]) else ""}</small>'
                     f'<p>{_e(m["descricao"])}</p><p class="muted">'
                     f'{T["ja_respondido"] if m["id"] in respondidos else T["ninguem_respondeu"]}'
                     f'{T["quem_trabalha"]}: {", ".join(_e(p["nome"]) for p in quem[:6]) or T["ninguem_ainda"]}</p></article>')
    if not ped_html:
        ped_html = f'<p class="muted">{T["nenhum_pedido"]}</p>'

    av_html = ''.join(f'<li>{_e(a)}</li>' for a in avisos or []) or f'<li>{T["nenhum_aviso"]}</li>'

    # ---- "posso ajudar" esperando apresentação (o que mais gera conexão real)
    itens = {txt(r.get('ID')): r for r in tec.get('Mural', [])}
    resp_html = ''
    for r in tec.get('Respostas do mural', []):
        if sim(r.get('Apresentação feita?')):
            continue
        item = itens.get(txt(r.get('ID do item')), {})
        autor, quem = txt(item.get('Nome')) or T['quem_publicou'], txt(r.get('Nome')) or T['alguem']
        titulo = txt(item.get('Título') or r.get('Item'))
        msg = T['msg_resposta'](_primeiro(autor), _primeiro(quem), titulo, txt(r.get('Mensagem')))
        resp_html += (f'<article class="ped"><b>{_e(quem)} → {_e(autor)}</b> <small>{T["sobre"]} "{_e(titulo)}"</small>'
                      f'<p class="muted">{T["contatos"]}: {_e(quem)} — {_e(r.get("Contato (privado)")) or T["sem_contato"]} · '
                      f'{_e(autor)} — {_e(item.get("Contato (privado)")) or T["sem_contato"]}</p>'
                      f'<textarea readonly rows="3">{_e(msg)}</textarea>{_botao(T, painel)}'
                      f'<small class="muted">{T["marque_feita_painel" if painel else "marque_feita"]}</small></article>')
    resp_html = resp_html or f'<p class="muted">{T["nenhuma_resposta"]}</p>'

    # ---- itens antigos (pedem confirmação)
    antigos = [m for m in publico['mural'] if m['status'] == 'aberto' and _dias(m['data'], agora) > 45]
    antigos_html = ''.join(f'<li>{_e(m["titulo"])} <small>({_e(m["autor"])}, {T["antigos_dias"](_dias(m["data"], agora))})</small></li>'
                           for m in antigos)
    antigos_html = (f'<p class="muted">{T["antigos_sub"]}</p><ul>{antigos_html}</ul>') if antigos else \
        f'<p class="muted">{T["nenhum_antigo"]}</p>'
    semana = mensagem_semana(publico, agora, site_url, idioma)

    return f'''<!doctype html><html lang="{T["lang"]}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>{_e(T["titulo_pagina"])}</title>
<style>
:root{{--bg:#F5EFE4;--panel:#FFFBF4;--ink:#2A1C13;--muted:#6E5B4C;--line:#E2D6C3;--accent:#B4532A;--ok:#2F6B3A}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,'Segoe UI',sans-serif}}
main{{max-width:1080px;margin:0 auto;padding:24px 16px 60px}}
h1{{font-family:Georgia,serif;margin:0}}h2{{font-family:Georgia,serif;margin:0 0 10px;font-size:20px}}
.top{{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;margin-bottom:6px}}
.top a{{color:var(--accent)}}
.priv{{background:#F4CCCC;color:#7a1f1f;padding:8px 12px;border-radius:8px;font-size:13px;margin:10px 0 20px}}
section{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:16px}}
.muted{{color:var(--muted);font-size:13px}}.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin-top:12px}}
.kpi{{border:1px solid var(--line);border-radius:10px;padding:10px 12px;background:#fff}}.kpi span{{font-size:12px;color:var(--muted);display:block}}
.kpi b{{font-size:24px;display:block}}.kpi small{{color:var(--muted)}}
.fases{{display:flex;gap:6px;list-style:none;padding:0;margin:10px 0;flex-wrap:wrap}}
.fases li{{padding:6px 12px;border-radius:999px;border:1px solid var(--line);font-size:13px;color:var(--muted)}}
.fases li.on{{background:var(--ink);color:#fff;border-color:var(--ink)}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}@media(max-width:760px){{.cols{{grid-template-columns:1fr}}}}
.sug,.ped{{border-top:1px solid var(--line);padding:12px 0}}.sug header{{display:flex;justify-content:space-between}}
.pts{{font-size:12px;color:var(--muted)}}.sug ul{{margin:6px 0;padding-left:18px;font-size:14px}}
textarea{{width:100%;font:inherit;font-size:13px;border:1px solid var(--line);border-radius:8px;padding:8px;background:#fff;color:var(--ink)}}
button{{font:inherit;font-size:13px;border:0;border-radius:8px;padding:6px 12px;background:var(--accent);color:#fff;cursor:pointer;margin:6px 8px 4px 0}}
ul.pend{{list-style:none;padding:0;margin:0}}ul.pend li{{padding:6px 0;border-bottom:1px solid var(--line)}}ul.pend li.alerta b{{color:var(--accent)}}
.funil{{display:flex;gap:8px;flex-wrap:wrap}}.etapa{{flex:1;min-width:110px;border:1px solid var(--line);border-radius:10px;padding:8px;text-align:center;background:#fff}}
.etapa b{{display:block;font-size:22px}}.etapa span{{font-size:12px;color:var(--muted)}}
table{{width:100%;border-collapse:collapse;font-size:14px}}td,th{{text-align:left;padding:6px;border-bottom:1px solid var(--line)}}
.spark{{color:var(--accent);vertical-align:middle;margin-left:8px}}
</style>{ESTILO_PAINEL if painel else ''}</head><body><main>
<div class="top"><h1>{_e(escopo_nome) if painel and escopo_nome else T["titulo"]}</h1><span class="muted">{T["rede"]} · {T["gerado"]} {_e(agora.strftime(T["formato_data"]))}{"" if painel else " · " + T["outro_idioma"]}</span></div>
<div class="priv">{T["privado_painel" if painel else "privado"]}</div>
{T["nota_planilha"]}
<section><h2>{T["saude"]}</h2>
<ol class="fases">{trilha}</ol>
<p><b>{_e(fase_nome)}.</b> {_e(fase_texto)}</p>
<p class="muted">{dep_txt} {sem_hub}</p>
<div class="kpis">{cards_html}</div></section>
{hist_html}
<section><h2>{T["esperando"]}</h2><ul class="pend">{pend}</ul>
<p class="muted">{T["esperando_rodape_painel" if painel else "esperando_rodape"]}</p></section>

<section><h2>{T["sugeridas"]}</h2>
<p class="muted">{T["sugeridas_sub"]}</p>
{sug_html}</section>

<section><h2>{T["funil"]}</h2><div class="funil">{funil_html}</div>
<p class="muted">{T["funil_sub"]}</p></section>

<section><h2>{T["posso_ajudar"]}</h2>{resp_html}</section>

<section><h2>{T["pedidos"]}</h2>{ped_html}</section>

<section><h2>{T["antigos"]}</h2>{antigos_html}</section>

<section><h2>{T["semana"]}</h2>
<p class="muted">{T["semana_sub"]}</p>
<textarea readonly rows="10">{_e(semana)}</textarea>{_botao(T, painel)}</section>

<div class="cols">
<section><h2>{T["pontes"]}</h2><p class="muted">{T["pontes_sub"]}</p><ol>{ponte}</ol></section>
<section><h2>{T["mais_conectadas"]}</h2><ol>{graus}</ol></section>
</div>
<section><h2>{T["isolados"](len(met["isolados"]))}</h2><p>{isol or T["ninguem"]}</p></section>
{"" if avisos is None else f'<section><h2>{T["avisos"]}</h2><ul>{av_html}</ul></section>'}
</main>
<script>{SCRIPT_PAINEL if painel else _script_arquivo(T)}</script>
</body></html>'''
