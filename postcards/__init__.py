import os
import logging

from flask import Flask

logging.basicConfig()
logging.getLogger('pycountry.db').setLevel(logging.CRITICAL)

app = Flask(__name__)
app.config.from_envvar('POSTCARD_SETTINGS')
app.secret_key = os.urandom(24)

# let us handle ssl better
# http://flask.pocoo.org/snippets/35/
class ReverseProxied(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        scheme = environ.get("HTTP_X_SCHEME")
        if scheme:
            environ["wsgi.url_scheme"] = scheme
        return self.app(environ, start_response)

app.wsgi_app = ReverseProxied(app.wsgi_app)

# make sure the views get registered
import postcards.views
