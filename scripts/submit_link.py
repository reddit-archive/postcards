#!/usr/bin/python

import urllib

from r2.models import Account, Subreddit, Link
from r2.lib.db import queries
from r2.lib.media import force_thumbnail
from r2.lib.amqp import worker


UPVOTE = True
def submit_link(user, subreddit, title, url, thumb_url):
    account = Account._by_name(user)
    subreddit = Subreddit._by_name(subreddit)
    ip = '127.0.0.1'

    # submit the link
    link = Link._submit(
        is_self=False,
        title=title,
        content=url,
        author=account,
        sr=subreddit,
        ip=ip,
        spam=False,
    )

    try:
        # force the thumbnail before scraper_q gets in the mix
        image_data = urllib.urlopen(thumb_url).read()
        force_thumbnail(link, image_data)
    except:
        pass

    # various backend processing things
    queries.new_link(link)
    link.update_search_index()

    # wait for the amqp worker to finish up
    worker.join()

    print link.make_permalink_slow()
