import json
import Image
import base64
import urllib
import hashlib
import cStringIO
import subprocess
from boto.s3.connection import S3Connection

from postcards import app
from postcards.models import db, Postcard
from postcards.lib.queue import processed_asynchronously

s3 = S3Connection(app.config['S3_ACCESS_KEY'], app.config['S3_SECRET_KEY'])
bucket = s3.get_bucket(app.config['S3_BUCKET'])

def s3_url_from_filename(filename):
    return 'http://' + app.config['S3_BUCKET'] + '.s3.amazonaws.com/' + filename

def upload_to_s3(filename, data, content_type):
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
        'scripts/' + command + '.py',
        '-c',
        command + '(' + ','.join(repr(x) for x in arguments) + ')'
    ])


@processed_asynchronously
def submit_link_to_postcard(postcard_id):
    postcard = Postcard._byID(postcard_id)

    title = "[Postcard] sent in from %s" % postcard.country

    postcard_url = 'http://www.reddit.com/about/postcards/%d' % postcard.id

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
    postcard = Postcard._byID(postcard_id)

    if postcard.front:
        postcard.front_thumb, _ = make_smaller_version_of_image(postcard.front)

    if postcard.back:
        postcard.back_thumb, _ = make_smaller_version_of_image(postcard.back)

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

@processed_asynchronously
def generate_jsonp():
    data = []
    dimensions = dict(small=(215, 215),
                      full=(800, 800))

    # build the json data and make sure the images are in place
    query = Postcard.query.filter_by(published=True, deleted=False)
    for postcard in query:
        # generate the images if necessary
        if not postcard.json_image_info:
            image_info = {}
            for side in ('front', 'back'):
                full_image_url = getattr(postcard, side)
                if not full_image_url:
                    continue

                image_info[side] = {}
                for size in ('small', 'full'):
                    img_data = make_smaller_version_of_image(full_image_url,
                                                             dimensions[size])
                    filename, (width, height) = img_data
                    image_info[side][size] = dict(filename=filename,
                                                  width=width,
                                                  height=height)

            postcard.json_image_info = json.dumps(image_info)
        else:
            image_info = json.loads(postcard.json_image_info)

        # add data to json_data
        data.append(dict(id=postcard.id,
                         date=str(postcard.date),
                         country=postcard.country,
                         latitude=str(postcard.latitude),
                         longitude=str(postcard.longitude),
                         images=image_info))

    # commit any changes
    db.session.commit()

    # upload the jsonp'd data to s3
    json_data = "postcards(" + json.dumps(data) + ")"
    upload_to_s3('postcards.js', json_data, 'application/javascript')
