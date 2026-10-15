"""Conversa com o Supabase sem dependências (só urllib), como o rnq/netlify.py.

- Banco (PostgREST): o pipeline do Mac chama só as funções rnq_pipeline_* com a chave SECRETA.
- Auth (GoTrue admin): convidar o primeiro admin.
- Management API (api.supabase.com): usada só pelo "painel_admin.py configurar", com o token pessoal.

A chave secreta e o token pessoal nunca são impressos nem gravados fora do .env.
"""
import json
import urllib.error
import urllib.parse
import urllib.request
import uuid

API_GESTAO = 'https://api.supabase.com/v1'
AGENTE = 'rnq-painel-admin'


class ErroSupabase(Exception):
    pass


def _cabecalhos_chave(chave):
    """Chaves novas (sb_secret_/sb_publishable_) vão só no 'apikey'; as antigas (JWT) também no Authorization."""
    h = {'apikey': chave, 'User-Agent': AGENTE}
    if chave.startswith('eyJ'):
        h['Authorization'] = f'Bearer {chave}'
    return h


def _pedir(url, metodo='GET', cabecalhos=None, corpo=None, abrir=urllib.request.urlopen, timeout=60, onde='Supabase'):
    dados = None
    h = dict(cabecalhos or {})
    if corpo is not None and not isinstance(corpo, (bytes, bytearray)):
        dados = json.dumps(corpo, ensure_ascii=False).encode('utf-8')
        h.setdefault('Content-Type', 'application/json')
    elif corpo is not None:
        dados = bytes(corpo)
    req = urllib.request.Request(url, data=dados, method=metodo, headers=h)
    try:
        with abrir(req, timeout=timeout) as r:
            bruto = r.read().decode('utf-8')
            return json.loads(bruto) if bruto.strip() else None
    except urllib.error.HTTPError as e:
        try:
            detalhe = e.read().decode('utf-8')[:400]
        except Exception:                                    # noqa: BLE001 — só para a mensagem
            detalhe = ''
        if e.code in (401, 403):
            raise ErroSupabase(f'{onde} recusou a chave ({e.code}). Confira o .env (veja docs/PAINEL-ADMIN.md). {detalhe}')
        if e.code == 404:
            raise ErroSupabase(f'{onde}: não encontrado (404). Rode "python3 painel_admin.py configurar". {detalhe}')
        raise ErroSupabase(f'{onde} respondeu {e.code}: {detalhe}')
    except urllib.error.URLError as e:
        raise ErroSupabase(f'Sem conexão com o {onde}: {e.reason}')


class Banco:
    """PostgREST + GoTrue admin de um projeto, com a chave secreta (só no Mac)."""

    def __init__(self, url, chave, abrir=urllib.request.urlopen):
        if not url or not chave:
            raise ErroSupabase('Faltam SUPABASE_URL e/ou SUPABASE_SECRET_KEY no .env')
        self.url = url.rstrip('/')
        self.chave = chave
        self.abrir = abrir

    def rpc(self, funcao, args=None, timeout=120):
        return _pedir(f'{self.url}/rest/v1/rpc/{funcao}', 'POST', _cabecalhos_chave(self.chave), args or {},
                      self.abrir, timeout, onde='Banco do painel')

    def convidar(self, email, redirecionar, dados=None):
        """Convite por e-mail (Supabase Auth). Devolve o id do usuário (novo ou que já existia)."""
        q = urllib.parse.urlencode({'redirect_to': redirecionar}) if redirecionar else ''
        try:
            r = _pedir(f'{self.url}/auth/v1/invite' + (f'?{q}' if q else ''), 'POST', _cabecalhos_chave(self.chave),
                       {'email': email, 'data': dados or {}}, self.abrir, onde='Login do painel')
            return (r or {}).get('id')
        except ErroSupabase as e:
            texto = str(e).lower()
            if '422' in texto or 'already' in texto or 'exists' in texto or 'registered' in texto:
                uid = self.rpc('rnq_usuario_por_email', {'p_email': email})
                if uid:
                    return uid
            raise


class Gestao:
    """Management API do Supabase (configurar o projeto). Precisa do token pessoal (SUPABASE_ACCESS_TOKEN)."""

    def __init__(self, token, ref, abrir=urllib.request.urlopen):
        if not token or not ref:
            raise ErroSupabase('Faltam SUPABASE_ACCESS_TOKEN e/ou SUPABASE_PROJECT_REF no .env')
        self.token = token
        self.ref = ref
        self.abrir = abrir

    def _h(self):
        return {'Authorization': f'Bearer {self.token}', 'User-Agent': AGENTE}

    def _p(self, caminho, metodo='GET', corpo=None, cabecalhos=None, timeout=120):
        h = self._h()
        h.update(cabecalhos or {})
        return _pedir(f'{API_GESTAO}/projects/{self.ref}{caminho}', metodo, h, corpo, self.abrir, timeout,
                      onde='Supabase (gestão)')

    def projeto(self):
        return self._p('')

    def sql(self, consulta):
        return self._p('/database/query', 'POST', {'query': consulta}, timeout=300)

    def configurar_auth(self, campos):
        return self._p('/config/auth', 'PATCH', campos)

    def chaves(self):
        return self._p('/api-keys?reveal=true') or []

    def segredos(self, pares):
        return self._p('/secrets', 'POST', [{'name': k, 'value': v} for k, v in pares.items()])

    def publicar_funcao(self, slug, arquivos, entrada='index.ts', verificar_jwt=True):
        """arquivos: {nome: texto}. Multipart como na documentação do endpoint functions/deploy."""
        limite = 'rnq' + uuid.uuid4().hex
        partes = []

        def parte(nome_campo, conteudo, nome_arquivo=None, tipo='application/json'):
            disp = f'form-data; name="{nome_campo}"' + (f'; filename="{nome_arquivo}"' if nome_arquivo else '')
            partes.append(f'--{limite}\r\nContent-Disposition: {disp}\r\nContent-Type: {tipo}\r\n\r\n'.encode()
                          + conteudo.encode('utf-8') + b'\r\n')
        parte('metadata', json.dumps({'entrypoint_path': entrada, 'name': slug, 'verify_jwt': verificar_jwt}))
        for nome, texto in arquivos.items():
            parte('file', texto, nome, 'application/typescript' if nome.endswith('.ts') else 'application/javascript')
        corpo = b''.join(partes) + f'--{limite}--\r\n'.encode()
        return self._p(f'/functions/deploy?slug={urllib.parse.quote(slug)}', 'POST', corpo,
                       {'Content-Type': f'multipart/form-data; boundary={limite}'}, timeout=300)


def escolher_chaves(lista):
    """Da lista da Management API, a chave pública (navegador) e a secreta (Mac). Prefere as novas."""
    def achar(*tipos):
        for t in tipos:
            for k in lista:
                nome, tipo, valor = k.get('name') or '', k.get('type') or '', k.get('api_key') or ''
                if valor and (tipo == t or nome == t):
                    return valor
        return ''
    publica = achar('publishable') or achar('anon')
    secreta = achar('secret') or achar('service_role')
    if not publica or not secreta:
        raise ErroSupabase('Não achei as chaves do projeto (publishable/secret). Confira o token pessoal.')
    return publica, secreta
