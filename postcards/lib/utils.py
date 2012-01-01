import boto
import Image
import base64
import urllib
import hashlib
import cStringIO
import subprocess

from postcards import app
from postcards.models import Postcard
from postcards.lib.queue import processed_asynchronously

s3 = boto.connect_s3()
bucket = s3.get_bucket(app.config['S3_BUCKET'])

def s3_url_from_filename(filename):
    return 'http://' + app.config['S3_BUCKET'] + '.s3.amazonaws.com/' + filename

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

def make_smaller_version_of_image(name, dimensions=(70,70)):
    url = s3_url_from_filename(name)
    image_bytes = urllib.urlopen(url).read()
    image_file = cStringIO.StringIO(image_bytes)
    image = Image.open(image_file)
    image.thumbnail(dimensions, Image.ANTIALIAS)
    output_file = cStringIO.StringIO()
    image.save(output_file, 'jpeg')
    return upload_to_s3(output_file.getvalue()), image.size

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
