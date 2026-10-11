"""Funções pequenas de texto, usadas em todo o pipeline."""
import hashlib
import re
import unicodedata


def slug(s):
    """'Diversidade, equidade & inclusão' -> 'diversidade-equidade-inclusao'."""
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def txt(v):
    """Valor de célula -> texto limpo ('' para vazio)."""
    if v is None:
        return ''
    if isinstance(v, str):
        return v.strip()
    return str(v).strip()


def chave_nome(nome):
    """Chave para casar nomes digitados por pessoas: sem acento, minúsculo, espaços simples."""
    s = unicodedata.normalize('NFKD', txt(nome)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]+', ' ', s)).strip()


def dividir(v):
    """'a; b, c\\nd' -> ['a', 'b', 'c', 'd'] (separadores: ; , quebra de linha). Mantém a ordem, sem repetidos."""
    out = []
    for parte in re.split(r'[;\n,]', txt(v)):
        p = parte.strip()
        if p and p not in out:
            out.append(p)
    return out


def dividir_areas(v):
    """Como dividir(), mas só por ; e quebra de linha — nomes de temas têm vírgula ('Estratégia, finanças...')."""
    out = []
    for parte in re.split(r'[;\n]', txt(v)):
        p = parte.strip()
        if p and p not in out:
            out.append(p)
    return out


def id_estavel(prefixo, *partes):
    """Identificador curto e estável para itens criados à mão na planilha (sem ID do Netlify)."""
    h = hashlib.sha1('|'.join(txt(p) for p in partes).encode('utf-8')).hexdigest()[:8]
    return f'{prefixo}-{h}'


def sim(v):
    return chave_nome(v) in ('sim', 's', 'yes', 'y', 'x', 'ok', 'true', '1')


def nao(v):
    return chave_nome(v) in ('nao', 'n', 'no', 'false', '0')


def curto(v, limite):
    """Corta texto público para não virar textão no card."""
    s = re.sub(r'\s+', ' ', txt(v))
    return s if len(s) <= limite else s[:limite - 1].rstrip() + '…'


def data_iso(v):
    """Aceita datetime, date ou texto ISO; devolve 'AAAA-MM-DD' ou ''."""
    if v is None or v == '':
        return ''
    if hasattr(v, 'strftime'):
        return v.strftime('%Y-%m-%d')
    m = re.match(r'(\d{4}-\d{2}-\d{2})', txt(v))
    if m:
        return m.group(1)
    m = re.match(r'(\d{2})/(\d{2})/(\d{4})', txt(v))
    if m:
        return f'{m.group(3)}-{m.group(2)}-{m.group(1)}'
    return ''


_EMAIL = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
_FONE = re.compile(r'(?:\+?\d[\d\s().-]{7,}\d)')


def sem_contato(v):
    """Tira e-mails e telefones de texto que vai para o site (a pessoa pode ter colado o contato na descrição).
    Devolve (texto_limpo, removeu?)."""
    s = txt(v)
    limpo = _EMAIL.sub('[contato removido]', s)
    limpo = _FONE.sub(lambda m: '[contato removido]' if sum(ch.isdigit() for ch in m.group()) >= 10 else m.group(),
                      limpo)
    return limpo, limpo != s
