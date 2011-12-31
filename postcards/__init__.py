import os

from flask import Flask

app = Flask(__name__)
app.config.from_envvar('POSTCARD_SETTINGS')
app.secret_key = os.urandom(24)

# make sure the views get registered
import postcards.views
