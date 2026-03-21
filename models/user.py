# models/user.py
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from flask import current_app

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(20))
    password_hash = db.Column(db.String(256), nullable=False)
    user_type = db.Column(db.String(20), default='visitor')  # 'visitor', 'admin'
    is_verified = db.Column(db.Boolean, default=False)
    agreed_to_policy = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6))
    verification_expiry = db.Column(db.DateTime)
    profile_image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    reviews = db.relationship('Review', backref='user', lazy=True)
    hotel_reviews = db.relationship('HotelReview', backref='user', lazy=True)
    bookings = db.relationship('Booking', backref='user', lazy=True)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def generate_token(self, expires_in=86400):
        """Generate JWT token"""
        try:
            payload = {
                'user_id': self.id,
                'user_type': self.user_type,
                'exp': datetime.utcnow() + timedelta(seconds=expires_in)
            }
            token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
            return token if isinstance(token, str) else token.decode('utf-8')
        except Exception as e:
            return None
    
    @staticmethod
    def verify_token(token):
        """Verify JWT token and return user"""
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            return User.query.get(payload['user_id'])
        except:
            return None
    
    def is_admin(self):
        """Check if user is admin"""
        return self.user_type == 'admin'
    
    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'phone_number': self.phone_number,
            'user_type': self.user_type,
            'is_verified': self.is_verified,
            'profile_image': self.profile_image,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }