from flaskext.sqlalchemy import SQLAlchemy

from postcards import app


db = SQLAlchemy(app)


class Postcard(db.Model):
    __tablename__ = 'postcards'
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(20))
    country = db.Column(db.String(3))
    date = db.Column(db.Date)
    latitude = db.Column(db.Numeric)
    longitude = db.Column(db.Numeric)
    front = db.Column(db.String)
    back = db.Column(db.String)
    front_thumb = db.Column(db.String)
    back_thumb = db.Column(db.String)
    deleted = db.Column(db.Boolean)
    published = db.Column(db.Boolean)
    tags = db.relationship("Tag")

    @staticmethod
    def _byID(id):
        return db.session.query(Postcard).filter_by(id=id).one()

    def _commit(self):
        db.session.commit()

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    postcard_id = db.Column(db.Integer, db.ForeignKey('postcards.id'))
    tag = db.Column(db.String)


class QueuedJob(db.Model):
    __tablename__ = 'queue'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    handler = db.Column(db.String, nullable=False)
    data = db.Column(db.String, nullable=False)
