import json
import Image
import base64
import urllib
import hashlib
import datetime
import pycountry
import cStringIO
import subprocess
from boto.s3.connection import S3Connection

from postcards import app
from postcards.models import db, Postcard
from postcards.lib.queue import processed_asynchronously

DEFAULT_DATE = datetime.date(2010, 01, 01)
CHUNK_SIZE = 28

def s3_url_from_filename(filename):
    return 'http://' + app.config['S3_BUCKET'] + '.s3.amazonaws.com/' + filename

def upload_to_s3(filename, data, content_type):
    s3 = S3Connection(app.config['S3_ACCESS_KEY'], app.config['S3_SECRET_KEY'])
    bucket = s3.get_bucket(app.config['S3_BUCKET'], validate=False)
    key = bucket.new_key(filename)
    key.set_contents_from_string(
        data,
        headers={'Content-Type': content_type},
        policy='public-read',
        replace=True,
    )

def upload_image_to_s3(bytes):
    digest = hashlib.sha1(bytes).digest()
    filename = base64.urlsafe_b64encode(digest[:8]).rstrip('=') + '.jpg'

    upload_to_s3(filename, bytes, 'image/jpeg')

    return filename

def make_smaller_version_of_image(name, dimensions=(70,70)):
    url = s3_url_from_filename(name)
    image_bytes = urllib.urlopen(url).read()
    image_file = cStringIO.StringIO(image_bytes)
    image = Image.open(image_file)
    image.thumbnail(dimensions, Image.ANTIALIAS)
    output_file = cStringIO.StringIO()
    image.save(output_file, 'jpeg')
    filename = upload_image_to_s3(output_file.getvalue())
    return filename, image.size

def run_reddit_script(command, arguments):
    return subprocess.check_output([
        'paster',
        '--plugin=r2',
        'run',
        app.config['REDDIT_CONFIG'],
        '/opt/postcards/scripts/' + command + '.py',
        '-c',
        command + '(' + ','.join(repr(x) for x in arguments) + ')'
    ])


@processed_asynchronously
def submit_link_to_postcard(postcard_id):
    postcard = Postcard._byID(postcard_id)

    country = pycountry.countries.get(alpha2=postcard.country)
    title_components = ["[Postcard] sent in from", country.name]
    if postcard.date != DEFAULT_DATE:
        title_components += ["on", postcard.date.strftime('%d-%b-%Y')]
    title = " ".join(title_components)

    postcard_url = 'http://www.reddit.com/about/postcards/view/%d' % postcard.id

    thumbnail = postcard.front_thumb or postcard.back_thumb
    assert thumbnail

    args = [app.config['REDDIT_USER'],
            app.config['REDDIT_SUBREDDIT'],
            title,
            postcard_url,
            s3_url_from_filename(thumbnail)]

    postcard.submission = run_reddit_script('submit_link', args)
    postcard._commit()

@processed_asynchronously
def generate_thumbnails(postcard_id, width=70, height=70):
    dimensions = dict(small=(215, 215),
                      full=(800, 800))

    postcard = Postcard._byID(postcard_id)

    if postcard.front:
        postcard.front_thumb, _ = make_smaller_version_of_image(postcard.front)

    if postcard.back:
        postcard.back_thumb, _ = make_smaller_version_of_image(postcard.back)

    image_info = {}
    for size in ('small', 'full'):
        image_info[size] = {}

        for side in ('front', 'back'):
            full_image_url = getattr(postcard, side)
            if not full_image_url:
                continue

            img_data = make_smaller_version_of_image(full_image_url,
                                                     dimensions[size])
            filename, (width, height) = img_data
            image_info[size][side] = dict(filename=filename,
                                          width=width,
                                          height=height)
    postcard.json_image_info = json.dumps(image_info)

    postcard._commit()


@processed_asynchronously
def send_gold_claim_message(postcard_id):
    postcard = Postcard._byID(postcard_id)
    assert postcard.submission

    run_reddit_script('send_claim_message', [postcard.user, postcard.submission])


@processed_asynchronously
def enflair_user(username):
    run_reddit_script('enflair', [app.config['REDDIT_SUBREDDIT'],
                                  username,
                                  "", "postcard-sender"])


def chunks(l, n):
    # http://stackoverflow.com/a/312464/190597
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]


@processed_asynchronously
def generate_jsonp():
    query = Postcard.query.filter_by(published=True, deleted=False).order_by(db.asc(Postcard.id))
    all_postcards = []
    for postcard in query:
        # make sure the images are in place
        if not postcard.json_image_info:
            continue

        # add the postcard data
        image_info = json.loads(postcard.json_image_info)
        data = dict(id=postcard.id,
                    date=str(postcard.date),
                    country=postcard.country,
                    latitude=str(postcard.latitude),
                    longitude=str(postcard.longitude),
                    images=image_info)
        all_postcards.append(data)

    # commit any changes
    db.session.commit()

    # output the chunks
    index = {}
    for chunk_id, chunk in enumerate(chunks(all_postcards, CHUNK_SIZE)):
        json_data = json.dumps(dict(chunk_id=chunk_id,
                                    postcards=chunk))
        upload_to_s3('postcards%d.js' % chunk_id,
                     'postcardCallback%d(%s)' % (chunk_id, json_data),
                     'application/javascript')

        range = (chunk[0]["id"], chunk[-1]["id"])
        index[chunk_id] = range

    # file containing latest postcards and an index mapping ids to chunks
    data = dict(total_postcard_count=len(all_postcards),
                index=index,
                postcards=all_postcards[-CHUNK_SIZE:])
    json_data = json.dumps(data)
    upload_to_s3('postcards-latest.js',
                 'postcardCallback(%s)' % json_data,
                 'application/javascript')

    # all the postcards in one file
    data = dict(postcards=all_postcards)
    json_data = json.dumps(data)
    upload_to_s3('postcards-all.js',
                 'postcardCallback(%s)' % json_data,
                 'application/javascript')
