import os

from flask import Flask

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////home/neil/projects/postcards/postcards.db'
app.secret_key = os.urandom(24)

# make sure the views get registered
import postcards.views
