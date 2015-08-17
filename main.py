import webapp2
import hashlib
import logging


LOG_FILENAME="server.log"
logging.basicConfig(filename=LOG_FILENAME,
	level=logging.INFO,
	)

class HelloWebapp2(webapp2.RequestHandler):
    def get(self):
	logging.info("Incoming Request: {0}, remote IP: {1}".format(
	    self.request.path_qs,
	    self.request.remote_addr
	    ))
        if self.request.params.has_key("echostr"):
	    token="8ce21d1d-daeb-4923-a885-fac9801670f4"
	    a=[token, self.request.params.get("timestamp"), self.request.params.get("nonce")]
	    a.sort()
	    sha1=hashlib.sha1(''.join(a)).hexdigest()
	    if sha1 == self.request.params.get("signature"):
		self.response.write(self.request.params.get("echostr"))
	    else:
		logging.warning("signature not match. Incoming sig: {0}, calculated sig: {1}".format(
		    self.request.params.get("signature"), sha1))
		self.response.status = '409 Conflict'
        else:
            self.response.headers['Content-Type']='text/plain'
            self.response.write('''Welcome to Ardenwood Coyote!
                    This page is supposed to be the API doc.''')

app = webapp2.WSGIApplication([
    ('/', HelloWebapp2),
], debug=True)

def main():
    from paste import httpserver
    httpserver.serve(app, host='0.0.0.0', port='80')

if __name__ == '__main__':
    main()

