import boto
import Image
import base64
import urllib
import hashlib
import cStringIO

from postcards.lib.queue import processed_asynchronously

s3 = boto.connect_s3()
BUCKET_NAME = 'postcards.reddit.com'
bucket = s3.get_bucket(BUCKET_NAME)


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
