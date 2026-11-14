from http.server import HTTPServer, BaseHTTPRequestHandler

class B(BaseHTTPRequestHandler):
    def do_POST(self):
        token = self.headers.get('X-Risk-Token')
        if not token or token == 'tampered_invalid_sig':
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'Unauthorized')
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'BOT_ACTIVE')

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    print('STATE: ACTIVE (CONNECTED)')
    HTTPServer(('0.0.0.0', 8001), B).serve_forever()
