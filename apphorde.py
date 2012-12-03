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
import random
import string

define("port", default=8888, type=int, help="port to listen on")

class Application(tornado.web.Application):
	def __init__(self):
		handlers = [
			(r"/", HomeHandler),
			(r"/tos", TosHandler),
			(r"/privacy", PrivacyHandler),
			(r"/contact", ContactHandler),
			(r"/register", RegisterHandler),
			(r"/login", LoginHandler),
			(r"/logout", LogoutHandler),
			(r"/dashboard", DashboardHandler),
			(r"/registerapp", RegisterAppHandler),
			(r"/thanks", BetaHandler),
			(r"/getad", GetAdHandler),
			(r"/click", ClickHandler),
			(r"/dev", DevHandler),
			(r"/editapp", EditAppHandler),
			(r"/myaccount", MyAccountHandler),
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
		self.render("index.html", ref=self.get_argument("ref", None), error=self.get_argument("error", None))

class TosHandler(BaseHandler):
	def get(self):
		self.render("tos.html", loggedin=self.current_user)
		
class PrivacyHandler(BaseHandler):
	def get(self):
		self.render("privacy.html", loggedin=self.current_user)
		
class ContactHandler(BaseHandler):
	def get(self):
		self.render("contact.html", loggedin=self.current_user)

class BetaHandler(BaseHandler):
	def post(self):
		email = self.get_argument("email", None)
		ref = self.get_argument("ref", None)
		if email and re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$", email):
			if self.db.beta_emails.find({'email': email}).count() == 0:
				if ref:
					self.db.beta_emails.update({'ref': ref}, {'$inc': {'count': 1}})
					ref = None
				while not ref or self.db.beta_emails.find({'ref': ref}, {'ref': 1}).count() != 0:
					ref = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(6))
				email_id = self.db.beta_emails.insert({'email': email, 'ref': ref, 'count': 0})
			else:
				ref = self.db.beta_emails.find_one({'email': email}, {'ref': 1})['ref']
			self.render("thanks.html", ref=ref)
		else:
			if ref:
				self.redirect('/?ref=' + ref + '&error=1')
			else:
				self.redirect("/?error=1")

class RegisterHandler(BaseHandler):
	def get(self):
		self.render("register.html", email="", beta_invite="", accept_tos="")
		
	def post(self):
		#validate registration info
		email = self.get_argument("email", None)
		password = self.get_argument("password", None)
		confirm_password = self.get_argument("confirm_password", None)
		beta_invite = self.get_argument("beta_invite", None)
		accept_tos = self.get_argument("accept_tos", None)
		errors = []
		if beta_invite and (beta_invite != "gojackets" and beta_invite != "yc" and beta_invite != "reddit"):
			errors.append("Invalid beta code. Are you sure you typed it in correctly?")
		elif not beta_invite: errors.append("Beta invite is required. <a href='/'>Get on the beta list</a>")
		if email:
			if not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$", email):
				errors.append("Email must be of the format 'something@something.xxx'.")
			else:
				if self.db.users.find({'email': email}).count() != 0:
					errors.append("The supplied email has already been registered.")
		else: errors.append("Email is required.")
		
		if password:
			if len(password) < 6:
				errors.append("Password must have a minimum of 6 characters.")
			else: 
				if confirm_password and password != confirm_password:
					errors.append("Password and password confirmation must match.")
		else: errors.append("Password is required")
		
		if not confirm_password: errors.append("Password confirmation is required.")
		
		if not accept_tos or accept_tos != "on":
			errors.append("You must agree to the Terms of Service to register.")
		
		if len(errors) == 0:
			#insert new user entry
			user_id = self.db.users.insert({'email': email, 'password': bcrypt.hashpw(password, bcrypt.gensalt()), 'apps': []})
			self.set_secure_cookie("user", user_id.binary, expires_days=1)
			self.redirect("/dashboard")
		else:
			self.render("register.html", 
				errors=errors, 
				email=email if email else "", 
				accept_tos=accept_tos if accept_tos else "",
				beta_invite=beta_invite if beta_invite else "")
	
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
				self.set_secure_cookie("user", user['_id'].binary, expires_days=1)
				self.redirect('/dashboard')
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
			apps = self.db.apps.find({'_id': {'$in': self.current_user['apps']}})
			self.render("dashboard.html", apps=apps)
			
class RegisterAppHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		self.render("registerapp.html")			
	
	@tornado.web.authenticated
	def post(self):
		name = self.get_argument("name", None)
		package = self.get_argument("package", None)	
		description = self.get_argument("description", None)
		icon_name = self.get_argument("icon_name", None)

		#validate app info
		errors = []
		if not name: 
			errors.append("App name is required")
		if not package: 
			errors.append("Package name is required")
		if description:
			if len(description) > 65: errors.append("Max ad text length is 65 characters")
		else:
			errors.append("Ad text is required")

		#validate uploaded icon
		if not icon_name: 
			errors.append("App icon is required")
		elif 'image/png' != self.get_argument("icon_content_type", None): 
			errors.append("App icon must be a PNG")

		if len(errors) == 0:
			from os import mkdir
			from shutil import move
			#generate dir name and create if necessary
			dest_dir = "static/icons/%s" % self.get_argument('icon_md5', '')[:6]
			if not os.path.exists(dest_dir):
				mkdir(dest_dir)
			
			#generate filename and move into place
			garbler = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(10))
			icon_name = '%s-%s.png' % (garbler, package)
			path = '%s/%s' % (dest_dir, icon_name)
			move(self.get_argument('icon_path'), path)
			
			#insert new app entry
			appId = None
			while not appId or self.db.apps.find({'appId': appId}, {'appId': 1}).count() != 0:
				appId = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(20))
			app_id = self.db.apps.insert({
				'appId': appId,
				'name': name, 
				'package': package,
				'icon_path': path,
				'desc': description,
				'random': random.random(), 
				'credits': 100, 
				'impressions': 0,
				'clicks': 0})
			self.db.users.update({'_id': self.current_user['_id']}, {'$push': {'apps': app_id}})
			self.redirect("/dashboard")
		else:
			self.render("registerapp.html", errors=errors)

class GetAdHandler(BaseHandler):
	def get(self):
		appId = self.get_argument('appid', None)
		if not appId:
			self.write('error')
			return
		
		inventory = self.db.apps.find({'appId': {'$ne': appId}, 'credits': {'$gte': 1}})
		count = inventory.count()
		if count == 0:
			#No inventory!
			return
		else:
			app = inventory.limit(-1).skip(int(random.random() * count)).next()
			self.db.apps.update({'_id': app['_id']}, {'$inc': {'impressions': 1, 'credits': -1}})
			self.write("OK APP\n%s\n%s\n%s\n%s" % (
				"http://apphorde.com/%s" % app['icon_path'], 
				app['appId'], 
				"market://details?id=%s" % app['package'], 
				app['desc']))
		
		#Give app credit it deserves
		self.db.apps.update({'appId': appId}, {'$inc': {'credits': 1}})
		
class ClickHandler(BaseHandler):
	def get(self):
		appId = self.get_argument('appid', None)
		if appId:
			self.db.apps.update({'appId': appId}, {'$inc': {'clicks': 1}})
			
class DevHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		self.render("dev.html")
		
class EditAppHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		appId = self.get_argument('id', None)
		if not appId:
			self.redirect("/dashboard")
		else:
			app = self.db.apps.find_one({'appId': appId})
			self.render("editapp.html", appId=app['appId'], name=app['name'], package=app['package'], adtext=app['desc'], image=app['icon_path'])
	
	@tornado.web.authenticated
	def post(self):
		name = self.get_argument("name", None)
		package = self.get_argument("package", None)	
		description = self.get_argument("description", None)
		icon_name = self.get_argument("icon_name", None)
		appId = self.get_argument("appid", None)
		print icon_name

		if not appId:
			self.redirect("/dashboard")
			return
			
		#validate new app info
		errors = []
		if not name: 
			errors.append("App name is required")
		if not package: 
			errors.append("Package name is required")
		if description:
			if len(description) > 65: errors.append("Max ad text length is 65 characters")
		else:
			errors.append("Ad text is required")

		#validate uploaded icon
		if icon_name and 'image/png' != self.get_argument("icon_content_type", None): 
			errors.append("App icon must be a PNG")

		if len(errors) == 0:
			icon_path = None
			if icon_name:
				from os import mkdir
				from shutil import move
				#generate dir name and create if necessary
				dest_dir = "static/icons/%s" % self.get_argument('icon_md5', '')[:6]
				if not os.path.exists(dest_dir):
					mkdir(dest_dir)
			
				#generate filename and move into place
				garbler = ''.join(random.choice(string.ascii_lowercase + string.digits) for x in range(10))
				icon_name = '%s-%s.png' % (garbler, package)
				path = '%s/%s' % (dest_dir, icon_name)
				move(self.get_argument('icon_path'), path)
			
				#Update app entry
				self.db.apps.update({'appId': appId}, {
					'$set': {
						'name': name,
						'package': package,
						'icon_path': path,
						'desc': description}})
			else:
				#Update app entry
				self.db.apps.update({'appId': appId}, {
					'$set': {
						'name': name,
						'package': package,
						'desc': description}})
			self.redirect("/dashboard")
		else:
			icon_path = self.db.apps.find_one({'appId': appId}, {'icon_path': 1})['icon_path']
			self.render("editapp.html", 
				errors=errors, 
				appId=appId if appId else "", 
				name=name if name else "", 
				package=package if package else "", 
				adtext=description if description else "", 
				image=icon_path if icon_path else "")

class MyAccountHandler(BaseHandler):
	@tornado.web.authenticated
	def get(self):
		self.render("myaccount.html", email=self.current_user['email'])
	
	@tornado.web.authenticated	
	def post(self):
		email = self.get_argument("email", None)
		old_password = self.get_argument("oldpassword", None)
		password = self.get_argument("password", None)
		confirm_password = self.get_argument("confirm_password", None);
		errors = []
		if not email:
			errors.append('Email cannot be blank')
		elif not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$", email):
			errors.append("Email must be of the format 'something@something.xxx'.")
		if not old_password:
			if password or confirm_password:
				errors.append("Current password must be supplied to change passwords.")
		elif (password and not confirm_password) or (confirm_password and not password):
			errors.append('New Password and Confirm New Password are required in order to change the current password.')
		elif password and confirm_password and password != confirm_password:
			errors.append('New password and new password confirmation must match.')
		elif password and confirm_password and password == confirm_password:
			if bcrypt.hashpw(old_password, self.current_user['password']) != self.current_user['password']:
				errors.append('The old password supplied is not correct, no updates were made to the user.')
		if len(errors) == 0:
			user = self.current_user
			self.db.users.update({'_id': user['_id']}, {'$set': {'email': email}})
			if password:
				self.db.users.update({'_id': user['_id']}, {'$set': {'password': bcrypt.hashpw(password, bcrypt.gensalt())}})
			self.render("myaccount.html", email=email, notifications=["Account successfully updated"])
		else:			
			self.render("myaccount.html", 
			errors=errors, 
			email=email if email else "")

if __name__ == "__main__":
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.instance().start()