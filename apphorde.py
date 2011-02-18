#!/usr/bin/env python
import tornado.httpserver
import tornado.httpclient
import tornado.ioloop
import tornado.web
from tornado.options import define, options
import tornado.options
import os.path
from pymongo import Connection
from pymongo.objectid import ObjectId
import re
import bcrypt

define("port", default=8888, type=int, help="port to listen on")

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r"/", HomeHandler),
			(r"/register", RegisterHandler),
			(r"/login", LoginHandler),
			(r"/logout", LogoutHandler),
			(r"/dashboard", DashboardHandler),
			(r"/newapp", NewAppHandler),
		]
		settings = {
			"static_path": os.path.join(os.path.dirname(__file__), "static"),
			"template_path": os.path.join(os.path.dirname(__file__), "templates"),
			#"ui_modules": uimodules,
			"xsrf_cookies": True,
			"cookie_secret": "0O[a0ggz2jt+s=j#cM[Dch~YdH*^AQz)m7#C#SxxMe=X",
			"login_url": "/login",
			"debug": True,
		}
		tornado.web.Application.__init__(self, handlers, **settings)
		
		self.db = Connection().apphorde
		
class BaseHandler(tornado.web.RequestHandler):
	@property
	def db(self):
		return self.application.db
		
	def get_current_user(self):
		user_id = self.get_secure_cookie("user")
		if not user_id: return None
		return self.db.users.find_one({'_id': ObjectId(user_id)})

class HomeHandler(BaseHandler):
	def get(self):
		self.render("index.html")
		
class RegisterHandler(BaseHandler):
	def get(self):
		self.render("register.html")
		
	def post(self):
		#validate registration info
		email = self.get_argument("email", None)
		password = self.get_argument("password", None)
		confirm_password = self.get_argument("confirm_password", None)
		accept_tos = self.get_argument("accept_tos", None)
		errors = []
		if email:
			if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$", email):
				errors.append("Email must be of the format 'something@something.xxx'.")
			else:
				if self.db.users.find({'email': email}).count() != 0:
					errors.append("The supplied email has already been registered. <a href='/recover'>Forgot your password?</a>")
		else: errors.append("Email is required.")
		
		if password:
			if len(password) < 6 or len(password) > 32:
				errors.append("Password must be 6-32 characters in length.")
			else: 
				if confirm_password and password != confirm_password:
					errors.append("Password and password confirmation must match.")
		else: errors.append("Password is required")
		
		if not confirm_password: errors.append("Password confirmation is required.")
		
		if not accept_tos or accept_tos != "on":
			errors.append("You must agree to the Terms of Service to register.")
		
		if len(errors) == 0:
			#insert new user entry
			user_id = self.db.users.insert({'email': email, 'password': bcrypt.hashpw(password, bcrypt.gensalt())})
			self.set_secure_cookie("user", user_id.binary)
			self.redirect("/dashboard")
		else:
			self.render("register.html", errors=errors)
	
class LoginHandler(BaseHandler):
	def get(self):
		if self.current_user:
			self.redirect("/dashboard")
		else:
			self.render("login.html")
		
	def post(self):
		email = self.get_argument("email", None)
		password = self.get_argument("password", None)
		errors = []
		if not email:
			errors.append('Email is required')
		if not password:
			errors.append('Password is required')
		if email and password:
			user = self.db.users.find_one({'email': email}, {'password': 1})
			if user and bcrypt.hashpw(password, user['password']) == user['password']:
				self.set_secure_cookie("user", user['_id'].binary)
				self.redirect("/dashboard")
				return
			else:
				errors.append('Invalid email/password')
		self.render("login.html", errors=errors)
			
class LogoutHandler(BaseHandler):
	def get(self):
		self.clear_cookie("user")
		self.redirect("/")
		
class DashboardHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		if not self.current_user['apps']:
			self.render("dashboard.html", notification="notification test")
		else:
			apps = self.db.apps.find({'_id': {'$in': self.current_user['apps']}}, {'name': 1, 'credits': 1, 'impressions': 1, 'clicks': 1})
			self.render("dashboard.html", apps=apps)
			
class NewAppHandler(BaseHandler):
	def get(self):
		self.render("newapp.html")

if __name__ == "__main__":
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()