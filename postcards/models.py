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
    front = db.Column(db.String(1000))
    back = db.Column(db.String(1000))
    front_thumb = db.Column(db.String(1000))
    back_thumb = db.Column(db.String(1000))
    deleted = db.Column(db.Boolean)
    published = db.Column(db.Boolean)
    submission = db.Column(db.String(1000))
    json_image_info = db.Column(db.String(1000))
    tags = db.relationship("Tag")

    @staticmethod
    def _byID(id):
        return db.session.query(Postcard).filter_by(id=id).one()

    def _commit(self):
        db.session.commit()

    @property
    def text_tags(self):
        return (tag.tag for tag in self.tags)

class Tag(db.Model):
    __tablename__ = 'tags'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    postcard_id = db.Column(db.Integer, db.ForeignKey('postcards.id'))
    tag = db.Column(db.String(1000))


class QueuedJob(db.Model):
    __tablename__ = 'queue'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    handler = db.Column(db.String(100), nullable=False)
    data = db.Column(db.String(1000), nullable=False)
