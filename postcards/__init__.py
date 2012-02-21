import os
import logging

from flask import Flask

logging.basicConfig()
logging.getLogger('pycountry.db').setLevel(logging.CRITICAL)

app = Flask(__name__)
app.config.from_envvar('POSTCARD_SETTINGS')
app.secret_key = os.urandom(24)

# make sure the views get registered
import postcards.views
