from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

from models import db 

class Destination(db.Model):
    __tablename__ = 'destinations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))
    region = db.Column(db.String(50))
    best_time_to_visit = db.Column(db.String(200))
    entry_fee = db.Column(db.String(100))
    opening_hours = db.Column(db.String(100))
    website = db.Column(db.String(200))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Use string references
    images = db.relationship('DestinationImage', backref='destination', lazy=True, cascade='all, delete-orphan')
    videos = db.relationship('DestinationVideo', backref='destination', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='destination', lazy=True, cascade='all, delete-orphan')
    hotels = db.relationship('Hotel', backref='destination', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description[:200] + '...' if len(self.description) > 200 else self.description,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'category': self.category,
            'region': self.region,
            'images': [img.to_dict() for img in self.images[:3]],
            'hotel_count': len(self.hotels),
            'review_count': len(self.reviews)
        }
    
    def to_dict_detail(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'category': self.category,
            'region': self.region,
            'best_time_to_visit': self.best_time_to_visit,
            'entry_fee': self.entry_fee,
            'opening_hours': self.opening_hours,
            'website': self.website,
            'images': [img.to_dict() for img in self.images],
            'videos': [vid.to_dict() for vid in self.videos],
            'reviews': [rev.to_dict() for rev in self.reviews[:10]],
            'hotels': [hotel.to_dict_basic() for hotel in self.hotels]
        }

class DestinationImage(db.Model):
    __tablename__ = 'destination_images'
    
    id = db.Column(db.Integer, primary_key=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id'))
    filename = db.Column(db.String(255))
    caption = db.Column(db.String(200))
    is_primary = db.Column(db.Boolean, default=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'url': f'/api/uploads/{self.filename}',
            'caption': self.caption,
            'is_primary': self.is_primary
        }

class DestinationVideo(db.Model):
    __tablename__ = 'destination_videos'
    
    id = db.Column(db.Integer, primary_key=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id'))
    youtube_id = db.Column(db.String(50))
    title = db.Column(db.String(200))
    thumbnail = db.Column(db.String(500))
    
    def to_dict(self):
        return {
            'id': self.id,
            'youtube_id': self.youtube_id,
            'title': self.title,
            'thumbnail': self.thumbnail
        }

class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    visit_date = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_name': self.user.full_name if self.user else 'Anonymous',
            'rating': self.rating,
            'comment': self.comment,
            'visit_date': self.visit_date,
            'created_at': self.created_at.isoformat()
        }