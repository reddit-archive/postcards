import json
import base64
import datetime

from flask import render_template, redirect, request, flash, abort
from flaskext import wtf

from postcards import app
from postcards.models import db, Postcard, Tag
from postcards.lib.utils import upload_image_to_s3, generate_thumbnails, submit_link_to_postcard, \
                                send_gold_claim_message, enflair_user, generate_jsonp


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
                         default=datetime.date.today())
    origin_country = wtf.HiddenField()
    origin_latitude = wtf.DecimalField()
    origin_longitude = wtf.DecimalField()
    front = wtf.TextField('front of card')
    back = wtf.TextField('back of card')
    tags = wtf.TextField('tags (comma-delimited)')


@app.context_processor
def add_site_nav():
    return dict(site_nav=[
        ("home", "home"),
        ("unpublished", "unpublished"),
        ("new_postcard_form", "add postcard"),
    ])


def build_pagination(base_query):
    page_number = int(request.args.get('page', 1))
    page_size = int(request.args.get('count', 25))
    pagination = base_query.paginate(page_number, per_page=page_size)
    return pagination


@app.route('/')
def home():
    base_query = (Postcard.query.filter(Postcard.deleted == False)
                                .options(db.subqueryload('tags'))
                                .order_by(db.desc(Postcard.date)))

    search_query = request.args.get('q')
    if search_query:
        base_query = base_query.filter(Postcard.user.like("%" + search_query + "%"))

    pagination = build_pagination(base_query)

    return render_template(
        'home.html',
        url_base='http://' + app.config['S3_BUCKET'] + '.s3.amazonaws.com/',
        DEFAULT_THUMB='noimage.png',
        pagination=pagination,
        search_query=search_query,
        current_page=".home",
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


@app.route('/unpublished', methods=['GET'])
def unpublished():
    base_query = (Postcard.query.filter(Postcard.deleted == False)
                                .filter(db.or_(Postcard.published == False,
                                               Postcard.published == None))
                                .options(db.subqueryload('tags'))
                                .order_by(db.asc(Postcard.date)))
    pagination = build_pagination(base_query)

    # patch in larger thumbnails
    for postcard in pagination.items:
        info = {}

        jsoninfo = getattr(postcard, 'json_image_info')
        if jsoninfo:
            info = json.loads(jsoninfo).get('small', {})

        postcard.front_thumb = info.get('front', {})
        postcard.back_thumb = info.get('back', {})

    return render_template(
        'unpublished.html',
        url_base='http://' + app.config['S3_BUCKET'] + '.s3.amazonaws.com/',
        DEFAULT_THUMB='noimage-large.png',
        DEFAULT_THUMB_WIDTH=215,
        DEFAULT_THUMB_HEIGHT=215,
        pagination=pagination,
        current_page=".unpublished",
    )


@app.route('/upload', methods=['POST'])
def upload():
    data = base64.b64decode(request.data)
    return upload_image_to_s3(data)


@app.route('/postcard/delete/<int:id>', methods=['POST', 'DELETE'])
def delete(id):
    postcard = Postcard._byID(id)
    if postcard.deleted or postcard.published:
        abort(403)
    postcard.deleted = True
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return 'success!'
    else:
        flash('postcard deleted!')
        return redirect('/')

@app.route('/postcard/publish/<int:id>', methods=['POST'])
def publish(id):
    postcard = Postcard._byID(id)
    if postcard.deleted or postcard.published:
        abort(403)
    postcard.published = True
    db.session.commit()

    generate_jsonp()
    submit_link_to_postcard(postcard.id)
    send_gold_claim_message(postcard.id)
    enflair_user(postcard.user)

    if request.headers['X-Requested-With'] == 'XMLHttpRequest':
        return 'success!'
    else:
        flash('postcard published!')
        return redirect('/')
