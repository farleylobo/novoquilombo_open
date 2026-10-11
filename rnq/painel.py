"""Painel do tecelão: HTML local, só para quem tece a rede. NUNCA publicar (tem contatos privados).

Responde, numa página:
1. Em que fase a rede está (Holley/Krebs) e o quanto ela depende de você.
2. Quem apresentar a quem esta semana — com motivo e mensagem pronta.
3. O que está esperando sua moderação.
4. Quais pedidos do mural ainda não têm ninguém, e quem no mapa pode ajudar.
"""
import html
from datetime import datetime

from . import config as C
from .rede import FASES
from .util import chave_nome, nao, sim, txt


def _e(s):
    return html.escape(txt(s))


def _pct(x):
    return f'{round(x * 100)}%'


def _primeiro(nome):
    return txt(nome).split(' ')[0] if nome else ''


def mensagem_apresentacao(pa, pb, motivo):
    def quem(p):
        cargo, org = txt(p.get('cargo')), txt(p.get('organizacao'))
        partes = [x for x in (cargo, org if org.lower() not in cargo.lower() else '') if x]
        return f'{p["nome"]}' + (f' ({", ".join(partes)})' if partes else '')
    return (f'Oi {_primeiro(pa["nome"])} e {_primeiro(pb["nome"])}! Quero apresentar vocês. '
            f'{quem(pa)} e {quem(pb)}. Acho que vale uma conversa porque {motivo}. '
            f'Topam um papo de 30 minutos? Me contem depois como foi. — Rede Novo Quilombo')


def _sparkline(valores, largura=220, altura=40):
    if len(valores) < 2:
        return ''
    mx, mn = max(valores), min(valores)
    faixa = (mx - mn) or 1
    pts = ' '.join(f'{i * largura / (len(valores) - 1):.1f},{altura - 4 - (v - mn) / faixa * (altura - 8):.1f}'
                   for i, v in enumerate(valores))
    return (f'<svg width="{largura}" height="{altura}" viewBox="0 0 {largura} {altura}" aria-hidden="true">'
            f'<polyline points="{pts}" fill="none" stroke="currentColor" stroke-width="2"/></svg>')


def pendencias(tec):
    def contar(aba, col, cond):
        return sum(1 for r in tec.get(aba, []) if cond(r.get(col)))
    vazio = lambda v: not txt(v)
    nao_sim = lambda v: not sim(v)
    return [
        ('Mural', 'itens esperando "Publicar?"', contar('Mural', 'Publicar?', vazio)),
        ('Respostas do mural', '"posso ajudar" sem apresentação feita', contar('Respostas do mural', 'Apresentação feita?', nao_sim)),
        ('Perfis', 'perfis esperando "Publicar?"', contar('Perfis', 'Publicar?', vazio)),
        ('Ligações sugeridas', 'ligações esperando "Aprovar?"', contar('Ligações sugeridas', 'Aprovar?', vazio)),
        ('Iniciativas', 'iniciativas esperando "Publicar?"', contar('Iniciativas', 'Publicar?', vazio)),
        ('Participações', 'pedidos de participação não encaminhados', contar('Participações', 'Encaminhado?', nao_sim)),
        ('Saídas', 'pedidos de saída (já aplicados)', contar('Saídas', 'Remover?', lambda v: not nao(v))),
    ]


def _dias(data_iso, agora):
    try:
        return (agora.date() - datetime.strptime(data_iso, '%Y-%m-%d').date()).days
    except (TypeError, ValueError):
        return 0


def mensagem_semana(publico, agora, site_url=''):
    """Texto pronto para colar nos grupos de WhatsApp: novidades dos últimos 7 dias + convite."""
    link = site_url.rstrip('/') if site_url else '<link do mapa>'
    novos = [m for m in publico['mural'] if m['status'] == 'aberto' and _dias(m['data'], agora) <= 7]
    inis = [i for i in publico['iniciativas'] if i['status'] == 'ativa' and _dias(i['data'], agora) <= 7]
    e = publico['estatisticas']
    linhas = ['*Rede Novo Quilombo — novidades da semana*', '',
              f'Somos {e["pessoas"]} pessoas, de {e["organizacoes"]} organizações, em {e["comunidades"]} comunidades.']
    pedidos = [m for m in novos if m['tipo'] == 'pedido']
    ofertas = [m for m in novos if m['tipo'] == 'oferta']
    if pedidos:
        linhas += ['', '*Pedidos — alguém pode ajudar?*'] + [f'• {m["titulo"]} ({m["autor"]})' for m in pedidos[:5]]
    if ofertas:
        linhas += ['', '*Ofertas*'] + [f'• {m["titulo"]} ({m["autor"]})' for m in ofertas[:5]]
    if inis:
        linhas += ['', '*Iniciativas novas*'] + [f'• {i["tipo"]}: {i["titulo"]}' for i in inis[:5]]
    if not (pedidos or ofertas or inis):
        linhas += ['', 'O mural está esperando você: o que você pode oferecer à rede? O que está precisando?']
    linhas += ['', f'Veja o mapa, publique no mural ou apresente alguém: {link}#mural',
               'Está no mapa e quer atualizar seu perfil ou sair? Busque seu nome e abra seu card.']
    return '\n'.join(linhas)


def gerar(publico, interno, tec, sugestoes, avisos, historico=None, agora=None, site_url=''):
    agora = agora or datetime.now()
    met = interno['metricas']
    por_id = {p['id']: p for p in publico['pessoas']}
    nome = lambda i: por_id[i]['nome'] if i in por_id else i
    tn = {t['id']: t['nome'] for t in publico['temas']}
    cn = {c['id']: c['nome'] for c in publico['comunidades']}
    hub = interno.get('hub')
    historico = historico or []

    # ---- saúde
    trilha = ''.join(f'<li class="{"on" if f == met["fase"] else ""}">{_e(FASES[f][0])}</li>'
                     for f in ('fragmentos', 'hub', 'multi-hub', 'nucleo'))
    dep_txt = (f'{_pct(met["dependencia_hub"])} das ligações passam por {_e(nome(hub))}.' if hub else
               'O hub configurado não está no mapa.')
    sem_hub = (f'Sem {_e(_primeiro(nome(hub)))}, a rede viraria {len(met["grupos_sem_hub"])} grupo(s) e '
               f'{met["isolados_sem_hub"]} pessoa(s) ficariam isoladas.' if hub else '')
    cards = [
        ('Pessoas conectadas', f'{met["conectadas"]}/{met["pessoas"]}', _pct(met['pct_conectadas']) + ' da rede'),
        ('Ligações', met['ligacoes'], f'{met["ligacoes_entre_comunidades"]} entre comunidades diferentes'),
        ('Grupos separados', len(met['grupos']), f'maior grupo: {met["maior_grupo"]} pessoas'),
        ('Caminho médio', f'{met["caminho_medio"]:.1f}', f'passos entre duas pessoas (máx. {met["diametro"]})'),
        ('Dependência do hub', _pct(met['dependencia_hub']), 'meta: abaixo de 30%'),
    ]
    cards_html = ''.join(f'<div class="kpi"><span>{_e(t)}</span><b>{_e(v)}</b><small>{_e(s)}</small></div>'
                         for t, v, s in cards)

    hist_html = ''
    if historico:
        serie = [h.get('pct_conectadas', 0) for h in historico]
        linhas = ''.join(
            f'<tr><td>{_e(h["data"])}</td><td>{h["pessoas"]}</td><td>{h["ligacoes"]}</td>'
            f'<td>{round(h["pct_conectadas"] * 100)}%</td><td>{round(h["dependencia_hub"] * 100)}%</td>'
            f'<td>{_e(h["fase_nome"])}</td></tr>' for h in historico[-12:][::-1])
        hist_html = (f'<section><h2>Evolução</h2><p class="muted">% de pessoas conectadas ao longo das atualizações '
                     f'<span class="spark">{_sparkline(serie)}</span></p><table><thead><tr><th>Data</th><th>Pessoas</th>'
                     f'<th>Ligações</th><th>Conectadas</th><th>Dep. hub</th><th>Fase</th></tr></thead>'
                     f'<tbody>{linhas}</tbody></table></section>')

    # ---- sugestões
    sug_html = ''
    for i, s in enumerate(sugestoes, 1):
        pa, pb = por_id[s['a']], por_id[s['b']]
        if s.get('temas'):
            nomes = [tn.get(t, t) for t in s['temas'][:2]]
            motivo = 'vocês dois trabalham com ' + ' e '.join(nomes)
        else:
            motivo = s['motivos'][0] if s['motivos'] else 'vocês têm muito em comum'
        msg = mensagem_apresentacao(pa, pb, motivo)
        sug_html += (
            f'<article class="sug"><header><b>{i}. {_e(pa["nome"])} ↔ {_e(pb["nome"])}</b>'
            f'<span class="pts">{s["pontos"]} pts</span></header>'
            f'<ul>{"".join(f"<li>{_e(m)}</li>" for m in s["motivos"])}</ul>'
            f'<textarea readonly rows="3">{_e(msg)}</textarea>'
            f'<button onclick="copiar(this)">Copiar mensagem</button>'
            f'<small class="muted">Depois de apresentar, registre na aba Apresentações: '
            f'Pessoa A = {_e(pa["nome"])}, Pessoa B = {_e(pb["nome"])}, Status = Apresentadas.</small></article>')
    if not sug_html:
        sug_html = '<p class="muted">Sem sugestões novas: todo par com tema em comum já está ligado ou registrado.</p>'

    # ---- pontes / conectores
    ponte = ''.join(f'<li>{_e(nome(v))} <small>{c:.2f}</small></li>' for v, c in met['intermediacao'][:8])
    graus = ''.join(f'<li>{_e(nome(v))} <small>{g} ligações</small></li>' for v, g in met['grau'][:8])
    isol = ', '.join(_e(nome(v)) for v in sorted(met['isolados'], key=nome))

    # ---- pendências
    pend = ''.join(f'<li class="{"alerta" if n else ""}"><b>{n}</b> {_e(desc)} <small>aba {_e(aba)}</small></li>'
                   for aba, desc, n in pendencias(tec))

    # ---- funil de apresentações
    funil = {s: 0 for s in C.STATUS_APRESENTACAO}
    for r in tec.get('Apresentações', []):
        st = next((s for s in C.STATUS_APRESENTACAO if chave_nome(s) == chave_nome(r.get('Status'))), None)
        if st:
            funil[st] += 1
    funil_html = ''.join(f'<div class="etapa"><b>{n}</b><span>{_e(s)}</span></div>' for s, n in funil.items())

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
        ped_html += (f'<article class="ped"><b>{_e(m["titulo"])}</b> <small>de {_e(m["autor"])} · {_e(m["data"])}'
                     f'{" · contato: " + _e(contatos.get(m["id"])) if contatos.get(m["id"]) else ""}</small>'
                     f'<p>{_e(m["descricao"])}</p><p class="muted">{"Já recebeu resposta. " if m["id"] in respondidos else "Ninguém respondeu ainda. "}'
                     f'Quem no mapa trabalha com isso: {", ".join(_e(p["nome"]) for p in quem[:6]) or "ninguém ainda"}</p></article>')
    if not ped_html:
        ped_html = '<p class="muted">Nenhum pedido aberto no mural.</p>'

    av_html = ''.join(f'<li>{_e(a)}</li>' for a in avisos) or '<li>Nenhum aviso.</li>'

    # ---- "posso ajudar" esperando apresentação (o que mais gera conexão real)
    itens = {txt(r.get('ID')): r for r in tec.get('Mural', [])}
    resp_html = ''
    for r in tec.get('Respostas do mural', []):
        if sim(r.get('Apresentação feita?')):
            continue
        item = itens.get(txt(r.get('ID do item')), {})
        autor, quem = txt(item.get('Nome')) or 'quem publicou', txt(r.get('Nome')) or 'alguém'
        msg = (f'Oi {_primeiro(autor)} e {_primeiro(quem)}! Quero apresentar vocês. {_primeiro(quem)} respondeu ao '
               f'"{txt(item.get("Título") or r.get("Item"))}" no mural da Rede Novo Quilombo'
               f'{": " + txt(r.get("Mensagem")) if txt(r.get("Mensagem")) else ""}. Combinem um papo e me contem como foi!')
        resp_html += (f'<article class="ped"><b>{_e(quem)} → {_e(autor)}</b> <small>sobre "{_e(item.get("Título") or r.get("Item"))}"</small>'
                      f'<p class="muted">Contatos: {_e(quem)} — {_e(r.get("Contato (privado)")) or "sem contato"} · '
                      f'{_e(autor)} — {_e(item.get("Contato (privado)")) or "sem contato"}</p>'
                      f'<textarea readonly rows="3">{_e(msg)}</textarea><button onclick="copiar(this)">Copiar mensagem</button>'
                      f'<small class="muted">Depois marque "Apresentação feita? = Sim" na aba Respostas do mural.</small></article>')
    resp_html = resp_html or '<p class="muted">Nenhuma resposta esperando.</p>'

    # ---- itens antigos (pedem confirmação)
    antigos = [m for m in publico['mural'] if m['status'] == 'aberto' and _dias(m['data'], agora) > 45]
    antigos_html = ''.join(f'<li>{_e(m["titulo"])} <small>({_e(m["autor"])}, {_dias(m["data"], agora)} dias)</small></li>'
                           for m in antigos)
    antigos_html = (f'<p class="muted">Abertos há mais de 45 dias. Pergunte a quem publicou se ainda vale; '
                    f'se não, marque "Status = Atendido".</p><ul>{antigos_html}</ul>') if antigos else \
        '<p class="muted">Nenhum item aberto há mais de 45 dias.</p>'
    semana = mensagem_semana(publico, agora, site_url)

    return f'''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>Painel do tecelão · RNQ</title>
<style>
:root{{--bg:#F5EFE4;--panel:#FFFBF4;--ink:#2A1C13;--muted:#6E5B4C;--line:#E2D6C3;--accent:#B4532A;--ok:#2F6B3A}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,-apple-system,'Segoe UI',sans-serif}}
main{{max-width:1080px;margin:0 auto;padding:24px 16px 60px}}
h1{{font-family:Georgia,serif;margin:0}}h2{{font-family:Georgia,serif;margin:0 0 10px;font-size:20px}}
.top{{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;margin-bottom:6px}}
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
</style></head><body><main>
<div class="top"><h1>Painel do tecelão</h1><span class="muted">Rede Novo Quilombo · gerado em {_e(agora.strftime("%d/%m/%Y %H:%M"))}</span></div>
<div class="priv">Documento interno: tem contatos privados. Não publique nem compartilhe este arquivo.</div>

<section><h2>Saúde da rede</h2>
<ol class="fases">{trilha}</ol>
<p><b>{_e(met["fase_nome"])}.</b> {_e(met["fase_texto"])}</p>
<p class="muted">{dep_txt} {sem_hub}</p>
<div class="kpis">{cards_html}</div></section>
{hist_html}
<section><h2>Esperando você</h2><ul class="pend">{pend}</ul>
<p class="muted">Tudo isso fica na planilha RNQ-tecelagem.xlsx.</p></section>

<section><h2>Apresentações sugeridas</h2>
<p class="muted">Critério (June Holley): tema em comum para gerar confiança, comunidade ou atuação diferente para trazer novidade.
Pares que unem grupos separados ou trazem alguém isolado valem mais. Você nunca aparece aqui: a ideia é a rede depender menos de você.
O impacto acontece quando você apresenta <b>e acompanha</b> — e melhor ainda se já sugerir algo concreto para fazerem juntos.</p>
{sug_html}</section>

<section><h2>Funil de apresentações</h2><div class="funil">{funil_html}</div>
<p class="muted">Registre cada apresentação na aba Apresentações. "Apresentadas", "Acompanhando" e "Colaborando" viram ligação no mapa.</p></section>

<section><h2>"Posso ajudar" esperando apresentação</h2>{resp_html}</section>

<section><h2>Pedidos do mural em aberto</h2>{ped_html}</section>

<section><h2>Itens antigos no mural</h2>{antigos_html}</section>

<section><h2>Mensagem da semana para os grupos</h2>
<p class="muted">Pronta para colar no WhatsApp: novidades dos últimos 7 dias e um convite para participar.</p>
<textarea readonly rows="10">{_e(semana)}</textarea><button onclick="copiar(this)">Copiar mensagem</button></section>

<div class="cols">
<section><h2>Pontes</h2><p class="muted">Quem mais está no caminho entre os outros (intermediação). Boas candidatas a tecer junto com você.</p><ol>{ponte}</ol></section>
<section><h2>Mais conectadas</h2><ol>{graus}</ol></section>
</div>
<section><h2>Ainda sem nenhuma ligação ({len(met["isolados"])})</h2><p>{isol or "Ninguém."}</p></section>
<section><h2>Avisos da última atualização</h2><ul>{av_html}</ul></section>
</main>
<script>function copiar(b){{const t=b.previousElementSibling;t.select();navigator.clipboard?.writeText(t.value);b.textContent='Copiado';setTimeout(()=>b.textContent='Copiar mensagem',1500)}}</script>
</body></html>'''
