import base64
import datetime

from flask import render_template, redirect, request, flash, abort
from flaskext import wtf

from postcards import app
from postcards.models import db, Postcard, Tag
from postcards.lib.utils import upload_to_s3, generate_thumbnails, submit_link_to_postcard


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
    page_number = int(request.args.get('page', 1))
    pagination = (Postcard.query.filter(Postcard.deleted == False)
                                .order_by(db.desc(Postcard.date))
                                .paginate(page_number, per_page=25))

    postcards = {}
    for postcard in pagination.items:
        postcards[postcard.id] = postcard

    for tag in Tag.query:
        if tag.postcard_id not in postcards:
            continue
        postcard = postcards[tag.postcard_id]
        if not hasattr(postcard, '_tags'):
            postcard._tags = []
        postcard._tags.append(tag.tag)

    return render_template(
        'home.html',
        postcards=postcards.values(),
        url_base='http://' + app.config['S3_BUCKET'] + '.s3.amazonaws.com/',
        DEFAULT_THUMB='noimage.png',
        pagination=pagination,
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
        postcard.back = form.back.data
        postcard.deleted = False
        db.session.add(postcard)

        for tag in (x.strip() for x in form.tags.data.split(',')):
            t = Tag()
            t.tag = tag
            postcard.tags.append(t)

        db.session.commit()

        generate_thumbnails(postcard.id)

        flash('postcard added!')
        return redirect('/postcard/new')
    return render_template('postcard_new.html', form=form)


@app.route('/upload', methods=['POST'])
def upload():
    data = base64.b64decode(request.data)
    return upload_to_s3(data)


@app.route('/postcard/delete', methods=['POST', 'DELETE'])
def delete():
    id = int(request.form['postcard-id'])
    postcard = Postcard._byID(id)
    if postcard.deleted or postcard.published:
        abort(403)
    postcard.deleted = True
    db.session.commit()
    flash('postcard deleted!')
    return redirect('/')

@app.route('/postcard/publish', methods=['POST'])
def publish():
    id = int(request.form['postcard-id'])
    postcard = Postcard._byID(id)
    if postcard.deleted or postcard.published:
        abort(403)
    postcard.published = True
    db.session.commit()

    submit_link_to_postcard(postcard.id)

    flash('postcard published!')
    return redirect('/')
