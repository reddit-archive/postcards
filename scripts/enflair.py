#!/usr/bin/python

from r2.models import Account, Subreddit, NotFound

def enflair(subreddit_name, account_name, flair_text, flair_class):
    sr = Subreddit._by_name(subreddit_name)

    try:
        account = Account._by_name(account_name)
    except NotFound:
        return

    sr.add_flair(account)

    setattr(account, "flair_%d_text" % sr._id, flair_text)
    setattr(account, "flair_%d_css_class" % sr._id, flair_class)
    account._commit()
