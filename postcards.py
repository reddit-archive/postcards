from flask import Flask
from flaskext.sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///postcards.db'
db = SQLAlchemy(app)

class Postcard(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(20))
    country = db.Column(db.String(3))
    date = db.Column(db.Date)
    latitude = db.Column(db.Numeric)
    longitude = db.Column(db.Numeric)

if __name__ == "__main__":
    app.run()
