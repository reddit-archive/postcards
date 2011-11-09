import boto
import hashlib
import base64
import os
import datetime
import urllib
import Image
import cStringIO
from flask import Flask, render_template, redirect, request, flash
from flaskext.sqlalchemy import SQLAlchemy
from flaskext import wtf

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///postcards.db'
app.secret_key = os.urandom(24)
db = SQLAlchemy(app)
s3 = boto.connect_s3()
BUCKET_NAME = 'postcards.reddit.com'
bucket = s3.get_bucket(BUCKET_NAME)

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
    front_thumb = db.Column(db.String)
    back_thumb = db.Column(db.String)
    deleted = db.Column(db.Boolean)
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
    #top_tags = (db.session.query(Tag)
                    #.filter(Tag.tag != '')
                    #.group_by(Tag.tag)
                    #.order_by(db.desc(db.func.count(Tag.tag)))
                    #.limit(10))

    postcards = {}
    for postcard in db.session.query(Postcard).filter(Postcard.deleted == False).order_by(db.desc(Postcard.date)):
        postcards[postcard.id] = postcard

    for tag in db.session.query(Tag):
        if tag.postcard_id not in postcards:
            continue
        postcard = postcards[tag.postcard_id]
        if not hasattr(postcard, '_tags'):
            postcard._tags = []
        postcard._tags.append(tag.tag)

    return render_template(
        'home.html',
        postcards=postcards.values(),
        url_base='http://' + BUCKET_NAME + '.s3.amazonaws.com/'
    )

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
        if postcard.front:
            postcard.front_thumb = thumbnail_image(postcard.front)
        postcard.back = form.back.data
        if postcard.back:
            postcard.back_thumb = thumbnail_image(postcard.back)
        postcard.deleted = False
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
    return upload_to_s3(data)

def upload_to_s3(data, content_type='image/jpeg'):
    digest = hashlib.sha1(data).digest()
    filename = base64.urlsafe_b64encode(digest[:8]).rstrip('=') + '.jpg'
    key = bucket.new_key(filename)
    key.set_contents_from_string(
        data,
        headers={'Content-Type': content_type},
        policy='public-read',
        replace=True,
    )
    return filename

def thumbnail_image(name):
    url = 'http://' + BUCKET_NAME + '.s3.amazonaws.com/' + name
    image_bytes = urllib.urlopen(url).read()
    image_file = cStringIO.StringIO(image_bytes)
    image = Image.open(image_file)
    image.thumbnail((70, 70), Image.ANTIALIAS)
    output_file = cStringIO.StringIO()
    image.save(output_file, 'jpeg')
    return upload_to_s3(output_file.getvalue())

@app.route('/postcard/delete', methods=['POST', 'DELETE'])
def delete():
    id = int(request.form['postcard-id'])
    postcard = db.session.query(Postcard).filter_by(id=id).one()
    postcard.deleted = True
    db.session.commit()
    return redirect('/')

if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)
