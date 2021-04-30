from http.server import HTTPServer, BaseHTTPRequestHandler
import log
import json
host = ('', 9999)

class Resquest(BaseHTTPRequestHandler):
	def do_GET(self):
		self.send_response(200)
		self.send_header('Content-type', 'application/json')
		self.end_headers()
		try:
			data = log.read_log("../logs")
		except err as e:
			data = str(e)
		self.wfile.write(json.dumps(data).encode())

if __name__ == '__main__':
    server = HTTPServer(host, Resquest)
    print("Starting server, listen at: %s:%s" % host)
    server.serve_forever()