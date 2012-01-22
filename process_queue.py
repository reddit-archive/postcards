#!/usr/bin/python

import sys

from postcards.lib.queue import handle_queued_jobs


filter = None
if len(sys.argv) > 2:
    print "USAGE: process_queue.py [filter]"
    sys.exit(1)
elif len(sys.argv) == 2:
    filter = sys.argv[1]

handle_queued_jobs()
