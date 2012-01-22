import json
import traceback

import sqlalchemy

from postcards.models import db, QueuedJob


queue_handlers = {}


def processed_asynchronously(fn):
    assert fn.__name__ not in queue_handlers
    queue_handlers[fn.__name__] = fn

    def queue_wrapper(*args, **kwargs):
        job = QueuedJob()
        job.handler = fn.__name__
        job.data = json.dumps((args, kwargs))

        db.session.add(job)
        db.session.commit()

    return queue_wrapper


def _handle_queued_job(job):
    handler = job.handler
    args, kwargs = json.loads(job.data)
    queue_handlers[handler](*args, **kwargs)


def handle_queued_jobs(filter=None):
    last_id = 0

    while True:
        try:
            query = (QueuedJob.query.filter(QueuedJob.id > last_id)
                                    .order_by(db.asc(QueuedJob.id))
                                    .limit(1))
            if filter:
                query = query.filter(QueuedJob.handler == filter)
            job = query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            break

        try:
            _handle_queued_job(job)
        except Exception:
            traceback.print_exc()
        else:
            db.session.delete(job)
            db.session.commit()

        last_id = job.id
