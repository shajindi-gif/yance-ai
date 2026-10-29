"""Fail-closed release fallback: public catalogue only; all customer writes 503."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return
    def respond(self, allow_catalogue):
        path=self.path.split('?',1)[0]
        if allow_catalogue and path=='/api/v1/products':
            body=Path('/catalogue.json').read_bytes(); status=200
        else:
            body=json.dumps({'detail':'系统升级维护中，请稍后重试；未执行任何业务写入。'},ensure_ascii=False).encode(); status=503
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('Retry-After','60')
        self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        self.respond(True)
    def do_POST(self):
        self.respond(False)
    do_PUT=do_POST
    do_PATCH=do_POST
    do_DELETE=do_POST
ThreadingHTTPServer(('0.0.0.0',8000),Handler).serve_forever()
