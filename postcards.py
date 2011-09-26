import boto
import hashlib
import base64
import os
import datetime
from flask import Flask, render_template, redirect, request, flash
from flaskext.sqlalchemy import SQLAlchemy
from flaskext import wtf

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///postcards.db'
app.secret_key = os.urandom(24)
db = SQLAlchemy(app)
s3 = boto.connect_s3()
bucket = s3.get_bucket('postcards.reddit.com')

class Postcard(db.Model):
    __tablename__ = 'postcards'
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(20))
    country = db.Column(db.String(3))
    date = db.Column(db.Date)
    latitude = db.Column(db.Numeric)
    longitude = db.Column(db.Numeric)
    front = db.Column(db.String)
    back = db.Column(db.String)
    tags = db.relationship("Tag")

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    postcard_id = db.Column(db.Integer, db.ForeignKey('postcards.id'))
    tag = db.Column(db.String)

class PostcardForm(wtf.Form):
    username = wtf.TextField(
        'username',
        validators=[
            wtf.Length(max=20),
            wtf.Required()
        ]
    )

    origin = wtf.TextField('origin', validators=[wtf.Required()])
    date = wtf.DateField('date of postmark',
                         format='%m/%d/%Y',
                         default=datetime.date(2010, 01, 01))
    origin_country = wtf.HiddenField()
    origin_latitude = wtf.DecimalField()
    origin_longitude = wtf.DecimalField()
    front = wtf.TextField('front of card')
    back = wtf.TextField('back of card')
    tags = wtf.TextField('tags (comma-delimited)')

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/postcard/new', methods=['GET', 'POST'])
def new_postcard_form():
    form = PostcardForm(request.form)
    if request.method == 'POST' and form.validate():
        postcard = Postcard()
        postcard.user = form.username.data
        postcard.date = form.date.data
        postcard.country = form.origin_country.data
        postcard.latitude = form.origin_latitude.data
        postcard.longitude = form.origin_longitude.data
        postcard.front = form.front.data
        postcard.back = form.back.data
        db.session.add(postcard)

        for tag in (x.strip() for x in form.tags.data.split(',')):
            t = Tag()
            t.tag = tag
            postcard.tags.append(t)

        db.session.commit()

        flash('postcard added!')
        return redirect('/postcard/new')
    return render_template('postcard_new.html', form=form)

@app.route('/upload', methods=['POST'])
def upload():
    data = base64.b64decode(request.data)
    digest = hashlib.sha1(data).digest()
    filename = base64.urlsafe_b64encode(digest[:8]).rstrip('=') + '.jpg'
    key = bucket.new_key(filename)
    key.set_contents_from_string(
        data,
        headers={'Content-Type': 'image/jpeg'},
        policy='public-read',
    )
    return filename

if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)
