import logging
import cgi
import urllib
from uuid import uuid4
import json

from google.appengine.ext import ndb
from google.appengine.api import urlfetch

import webapp2


DEFAULT_SCOREBOARD_NAME = 'default_scoreboard'
NEXUS_ENDPOINT = 'https://antelope.ears.ea.com'
SESSION_COOKIE_KEY = 'session_id'

# We set a parent key on the 'Scores' to ensure that they are all
# in the same entity group. Queries across the single entity group
# will be consistent.  However, the write rate should be limited to
# ~1/second.

def scoreboard_key(scoreboard_name=DEFAULT_SCOREBOARD_NAME):
    return ndb.Key('scoreboard', scoreboard_name)


#class Author(ndb.Model):
#    """Sub model for representing an author."""
#    identity = ndb.StringProperty(indexed=False)
#    email = ndb.StringProperty(indexed=False)


class Score(ndb.Model):
    #id = ndb.IntegerProperty(indexed=True)
    sessionid = ndb.StringProperty(indexed=False)
    score = ndb.IntegerProperty(indexed=False)


class MainHandler(webapp2.RequestHandler):
    def get(self):
	self.response.headers['Content-Type']='text/plain'
	self.response.write('''Welcome to the scoreboard!
	This page is supposed to be the API doc.''')


ACCESS_TOKEN_CACHE = {}


class ScoreHandler(webapp2.RequestHandler):

    def bad_request(self):
	self.response.status = '400 Bad Request'
	self.response.headers['Content-Type']='application/json'
	self.response.write('{"error":"invalid_request","error_description":"something is missing"}')


    def not_found(self):
	self.response.status = '404 Not Found'
	self.response.headers['Content-Type']='application/json'
	self.response.write('{"error":"id_not_found","error_description":"cannot find relevant score record"}')


    def session_changed(self):
	self.response.status = '409 Conflict'
	self.response.headers['Content-Type']='application/json'
	self.response.write('{"error":"session_changed","error_description": "Session moved or expired or not exist"}')


    def crack_token(self):
	at = self.request.get("access_token", None)
	if at is None:
	    self.bad_request()
	    return

	if not ACCESS_TOKEN_CACHE.has_key(at):
	    path = NEXUS_ENDPOINT + '/connect/tokeninfo?access_token={0}'.format(at)
	    logging.info("fetch {0}".format(path))
	    r = urlfetch.fetch(path)
	    logging.info("received {0}, {1}".format(r.status_code, r.content))
	    if r.status_code > 200:
		self.response.write(r.content)
		logging.error("crack token failed. Response: {0}".format(r.content))
		return
	    ACCESS_TOKEN_CACHE[at] = json.loads(r.content)
	else:
	    logging.info("ACCESS_TOKEN_CACHE hit. at={0}".format(at))
	return ACCESS_TOKEN_CACHE[at]


    def get(self):
	# crack access_token
	tokeninfo = self.crack_token()
	if tokeninfo is None:
	    return

	# persona id
	is_getting_others = False
	if self.request.params.has_key('key'):
	    persona_id = int(self.request.params.get('key'))
	    is_getting_others = True
	else:
	    persona_id = tokeninfo['persona_id']
	logging.info('persona_id = {0}'.format(persona_id))

	# get (id, session, score)
	db_score = ndb.Key(Score, persona_id).get()
	is_score_dirty = False
	if db_score is None:
	    if is_getting_others:
		self.not_found()
		return
	    else:
		logging.info('creating new score record')
		db_score = Score(id = tokeninfo['persona_id'],
			sessionid = None,
			score = 0)
		is_score_dirty = True
	else:
	    logging.info("Got existing score: {0}".format(
		json.dumps(db_score.to_dict())))

	# compare session
	is_new_session = False
	if not is_getting_others:
	    session_id = self.request.cookies.get(SESSION_COOKIE_KEY, None)
	    if session_id is None:
		session_id = str(uuid4())
		logging.info("issuing new session_id={0}".format(session_id))
		is_new_session = True
	    else:
		logging.info("existing session_id from cookie={0}".format(session_id))
	    
	    if is_new_session or db_score.sessionid is None:
		db_score.sessionid = session_id
		is_score_dirty = True
		
	    if is_new_session is False and db_score.sessionid != session_id:
		logging.info("session not matching. db_score.sessionid = {0}, session_id = {1}".format(db_score.sessionid, session_id))
		self.session_changed()
		return

	# return score
	self.response.status= '200 OK'
	self.response.headers['Content-Type']='application/json'
	if is_new_session is True:
	    self.response.headers.add_header(
		    'Set-Cookie',
		    '{0}={1}'.format(SESSION_COOKIE_KEY,db_score.sessionid))
	self.response.body=json.dumps(db_score.to_dict())

	# write db
	if is_score_dirty is True:
	    logging.info('writing score to db: {0}'.format(json.dumps(db_score.to_dict())))
	    db_score.put()


    def put(self):
	# validation
	if not self.request.params.has_key('score'):
	    self.bad_request()
	    return

	# crack token
	tokeninfo = self.crack_token()
	if tokeninfo is None:
	    self.bad_request()
	    return

	# get db_Score
	db_score = ndb.Key(Score, tokeninfo['persona_id']).get()
	if db_score is None:
	    self.not_found()
	    return

	# session_id check
	session_id = self.request.cookies.get(SESSION_COOKIE_KEY, None)
	if session_id is None:
	    self.bad_request()
	    return
	if session_id != db_score.sessionid:
	    self.session_changed()
	    return

	# write db
	in_score = int(self.request.params.get('score'))
	if in_score != db_score.score:
	    db_score.score = in_score
	    db_score.put()

	# return response
	self.response.headers['Content-Type'] = 'application/json'
	self.response.write(json.dumps(db_score.to_dict()))


    def delete(self):
	self.response.delete_cookie(SESSION_COOKIE_KEY)


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/score', ScoreHandler),
], debug=True)


