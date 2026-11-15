"""Separate HTTP wait service; real socket I/O, controlled service time."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
import time,socket
class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def setup(self):
        super().setup();self.connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
    def do_GET(self):
        ms=float(parse_qs(urlparse(self.path).query).get('ms',['3'])[0]);time.sleep(min(max(ms,0),100)/1000)
        data=b'ok';self.send_response(200);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def log_message(self,*args):pass
if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',18391),Handler).serve_forever()
