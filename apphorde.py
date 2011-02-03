#!/usr/bin/env python
import tornado.httpserver
import tornado.httpclient
import tornado.ioloop
import tornado.web
from tornado.options import define, options
import tornado.options
import os.path

define("port", default=8888, type=int, help="port to listen on")

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r"/", HomeHandler),
			(r"/newest", HomeHandler),
			(r"/how", HowHandler),
			(r"/signin", SignInHandler),
			(r"/start", SignUpHandler),
		]
		settings = {
			"static_path": os.path.join(os.path.dirname(__file__), "static"),
			"template_path": os.path.join(os.path.dirname(__file__), "templates"),
			"ui_modules": uimodules,
			"debug": True,
		}
		tornado.web.Application.__init__(self, handlers, **settings)
		
class HomeHandler(RequestHandler):
	def get(self):
		self.render("index.html")	

if __name__ == "__main__":
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()