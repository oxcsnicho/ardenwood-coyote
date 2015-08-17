import webapp2
import hashlib
import logging


LOG_FILENAME="server.log"
logging.basicConfig(filename=LOG_FILENAME,
	level=logging.DEBUG,
	)

class HelloWebapp2(webapp2.RequestHandler):
    def get(self):
        if self.request.params.has_key("echostr"):
	    '''
	    token="8ce21d1d-daeb-4923-a885-fac9801670f4"
	    a=[token,
		    self.request.params.get("timestamp"),
		    self.request.params.get("nounce")].sort()
	    sha1=hashlib.sha1(''.join(a)).hexdigest()
	    '''
	    logging.info("echostr Request: " + self.request.url)
            self.response.write(self.request.params.get("echostr"))
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

