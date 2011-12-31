import boto
import Image
import base64
import urllib
import hashlib
import cStringIO

from postcards import app
from postcards.models import Postcard
from postcards.lib.queue import processed_asynchronously

s3 = boto.connect_s3()
bucket = s3.get_bucket(app.config['S3_BUCKET'])


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
    url = 'http://' + app.config['S3_BUCKET'] + '.s3.amazonaws.com/' + name
    image_bytes = urllib.urlopen(url).read()
    image_file = cStringIO.StringIO(image_bytes)
    image = Image.open(image_file)
    image.thumbnail(dimensions, Image.ANTIALIAS)
    output_file = cStringIO.StringIO()
    image.save(output_file, 'jpeg')
    return upload_to_s3(output_file.getvalue()), image.size

@processed_asynchronously
def generate_thumbnails(postcard_id, width=70, height=70):
    postcard = Postcard._byID(postcard_id)

    if postcard.front:
        postcard.front_thumb, _ = make_smaller_version_of_image(postcard.front)

    if postcard.back:
        postcard.back_thumb, _ = make_smaller_version_of_image(postcard.back)

    postcard._commit()
