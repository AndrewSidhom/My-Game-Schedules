from flask_sqlalchemy import SQLAlchemy
from app import app

db = SQLAlchemy(app)


def row2dict(row):
    return {c.name: str(getattr(row, c.name)) for c in row.__table__.columns}


users_teams = db.Table('users_teams',
                       db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
                       db.Column('team_id', db.Integer, db.ForeignKey('team.id')))


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text(), nullable=False)
    fav_teams = db.relationship(
        'Team',
        secondary=users_teams,
        backref=db.backref('users', lazy='dynamic')
    )

    def __repr__(self):
        return "<User {}: {}>".format(self.id, self.name)


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text(), nullable=False)
    ranking = db.Column(db.Integer)

    def __repr__(self):
        return "<Team {}: {}, League ranking: {}>".format(self.id, self.name, self.ranking)


class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime)
    team1_id = db.Column(db.Integer, db.ForeignKey('team.id'))
    team2_id = db.Column(db.Integer, db.ForeignKey('team.id'))