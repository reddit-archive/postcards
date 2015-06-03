#!/usr/bin/python

import time
import datetime

from pylons import g
from r2.models import Account, create_unclaimed_gold, send_system_message, NotFound
from r2.lib.utils import randstr


REWARD = 31  # days of gold
TEMPLATE = """
Thanks for sending us [the postcard](%(postcard_url)s). You can pick
up your trophy [here](%(claim_url)s). If you have any questions, you
can write to %(gold_support_email)s.
"""


def send_claim_message(username, postcard_url):
    # this is ripped off from the gold-record.py code in reddit-private
    timestamp = int(time.time())
    now = datetime.datetime.now(g.tz)
    transaction_id = "M%d" % timestamp
    secret = "p_%d%s" % (timestamp, randstr(5))
    create_unclaimed_gold(transaction_id, "", "manual-unclaimed",
                          0, REWARD, secret, now, None)

    claim_url = "http://www.reddit.com/thanks/" + secret

    try:
        user = Account._by_name(username)
    except NotFound:
        print "User %r not found :(" % username
        return

    message = TEMPLATE % dict(postcard_url=postcard_url,
                              claim_url=claim_url,
                              gold_support_email=g.goldsupport_email)
    send_system_message(user, "we got that postcard you sent us!", message)
