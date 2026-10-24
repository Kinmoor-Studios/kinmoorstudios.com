# Local stand-in for GitHub Pages: gzip for text, Cache-Control max-age=600, same file layout.
import http.server, gzip, io, os, sys
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control','max-age=600'); super().end_headers()
    def send_head(self):
        path=self.translate_path(self.path)
        if os.path.isdir(path): path=os.path.join(path,'index.html')
        if path.endswith(('.html','.txt','.css','.js')) and 'gzip' in self.headers.get('Accept-Encoding','') and os.path.exists(path):
            data=gzip.compress(open(path,'rb').read(),9)
            self.send_response(200); self.send_header('Content-Type',self.guess_type(path)); self.send_header('Content-Encoding','gzip'); self.send_header('Content-Length',str(len(data))); self.end_headers()
            return io.BytesIO(data)
        return super().send_head()
os.chdir(sys.argv[1]); http.server.ThreadingHTTPServer(('127.0.0.1',int(sys.argv[2])),H).serve_forever()
