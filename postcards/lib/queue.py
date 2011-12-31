import json

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


def handle_queued_jobs():
    while True:
        try:
            job = db.session.query(QueuedJob).order_by(db.asc(QueuedJob.id)).limit(1).one()
        except sqlalchemy.orm.exc.NoResultFound:
            break

        _handle_queued_job(job)

        db.session.delete(job)
        db.session.commit()
