require('http').createServer((_, r) => {
  r.setHeader('Content-Type', 'text/html');
  r.end('<h1>Forex Bot (Python)</h1><p>This project is a Python trading bot — no web app in this repo.</p>');
}).listen(8080, () => console.log('listening on 8080'));
