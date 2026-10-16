// Servidor local mínimo do painel admin para os testes: serve admin/ com os mesmos cabeçalhos do Netlify
// (lidos de admin/_headers), para a Content-Security-Policy valer de verdade no navegador.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';

const TIPOS = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8',
                '.png': 'image/png', '.woff2': 'font/woff2', '.txt': 'text/plain; charset=utf-8', '.svg': 'image/svg+xml' };

export function cabecalhos(pasta) {
  const out = {};
  for (const linha of fs.readFileSync(path.join(pasta, '_headers'), 'utf8').split('\n')) {
    const m = linha.match(/^\s+([A-Za-z-]+):\s*(.+)$/);
    if (m) out[m[1]] = m[2].trim();
  }
  return out;
}

export function servir(pasta, { extras = {}, porta = 0 } = {}) {
  const base = cabecalhos(pasta);
  const srv = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://x');
    let rel = decodeURIComponent(url.pathname).replace(/^\/+/, '') || 'index.html';
    if (extras[rel] !== undefined) {
      res.writeHead(200, { ...base, 'Content-Type': TIPOS[path.extname(rel)] || 'text/plain' });
      return res.end(extras[rel]);
    }
    const arq = path.join(pasta, rel);
    if (!arq.startsWith(pasta) || !fs.existsSync(arq) || fs.statSync(arq).isDirectory()) {
      res.writeHead(404, base); return res.end('não encontrado');
    }
    res.writeHead(200, { ...base, 'Content-Type': TIPOS[path.extname(arq)] || 'application/octet-stream' });
    fs.createReadStream(arq).pipe(res);
  });
  return new Promise(ok => srv.listen(porta, '127.0.0.1', () => ok({ srv, url: `http://127.0.0.1:${srv.address().port}` })));
}
