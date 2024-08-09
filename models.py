from db import db

class Map(db.Model):
    __tablename__ = 'maps'
    map_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    tier = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String, nullable=False)
    mapper = db.Column(db.String, nullable=True)
    youtube = db.Column(db.String, nullable=True)
    stages = db.Column(db.String, nullable=True)  # Changed to String to match schema
    bonuses = db.Column(db.Integer, nullable=True)  # Changed to Integer to match schema
    ratings = db.relationship('Rating', backref='map', lazy=True)

class Rating(db.Model):
    __tablename__ = 'ratings'
    map_id = db.Column(db.Integer, db.ForeignKey('maps.map_id'), primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    rating = db.Column(db.Float, nullable=True)
    tier = db.Column(db.Float, nullable=True)
    surftype = db.Column(db.String, nullable=True)
    # Removed the 'id' field as primary key is a composite key of (map_id, userid)

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    googleid = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String, nullable=True)  # Made nullable to match schema
    ratings = db.relationship('Rating', backref='user', lazy=True)

class Profile(db.Model):
    __tablename__ = 'profile'
    profile_id = db.Column(db.Integer, primary_key=True)  # Changed to profile_id
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    username = db.Column(db.String, nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.Integer, nullable=True)

