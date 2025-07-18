# app/models.py
from .extensions import db
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from typing import List, TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from sqlalchemy.orm import Query

# friend table
friend = db.Table(
    'friend',
    db.Column('user_id',   db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('friend_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
)

class User(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(63),  nullable=False)
    lastname  = db.Column(db.String(63),  nullable=False)
    username  = db.Column(db.String(255), nullable=False, unique=True)
    email     = db.Column(db.String(255), nullable=False, unique=True)

    friends = db.relationship(
        'User',
        secondary=friend,
        primaryjoin=(friend.c.user_id   == id),
        secondaryjoin=(friend.c.friend_id == id),
        backref='friended_by'
    )

    maps = db.relationship(
        'Map',
        back_populates='user',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    activities = db.relationship(
        'Activity',
        back_populates='user',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    def to_dict(self):
        return {
            'id':        self.id,
            'firstname': self.firstname,
            'lastname':  self.lastname,
            'username':  self.username,
            'email':     self.email,
            'friends':   [f.id for f in self.friends]  # type: ignore
        }


class Map(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title= db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    image_path = db.Column(db.String(256), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    latitude    = db.Column(db.Float, nullable=False)
    longitude   = db.Column(db.Float, nullable=False)
    num_points = db.Column(db.Integer, nullable=False)
    uploaded_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    user = db.relationship(
        'User',
        back_populates='maps'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'image_path': self.image_path,
            'user_id': self.user_id,
            'latitude':    self.latitude,
            'longitude':   self.longitude,
            'num_points':  self.num_points,
            'uploaded_at': self.uploaded_at.isoformat()
        }

    @hybrid_method
    def distance_to(self, lat, lon):  # type: ignore
        """Instance-level: not used in query context."""
        # simple Python fallback if you ever call m.distance_to(...)
        from math import radians, sin, cos, asin, sqrt
        lat1, lon1 = radians(self.latitude), radians(self.longitude)
        lat2, lon2 = radians(lat),          radians(lon)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
        return 6371.0 * 2 * asin(sqrt(a))

    @distance_to.expression
    def distance_to(cls, lat, lon):  # type: ignore
        """SQL expression for ORDER BY in the database."""
        # Haversine formula in SQL
        return 6371.0 * 2 * func.asin(func.sqrt(
            func.pow(func.sin((func.radians(cls.latitude) - func.radians(lat)) / 2), 2) +
            func.cos(func.radians(cls.latitude)) * func.cos(func.radians(lat)) *
            func.pow(func.sin((func.radians(cls.longitude) - func.radians(lon)) / 2), 2)
        ))
        
class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title= db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    map_id = db.Column(db.String(36), db.ForeignKey('map.id'), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    distance = db.Column(db.Float, nullable=True)
    elapsed_time = db.Column(db.Float, nullable=True)
    
    user = db.relationship(
        'User',
        back_populates='activities'
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'user_id': self.user_id,
            'map_id': self.map_id,
            'created_at': self.created_at.isoformat(),
            'distance': self.distance,
            'elapsed_time': self.elapsed_time
        }
    
