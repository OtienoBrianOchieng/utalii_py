# models/hotel.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Association table for hotel amenities
hotel_amenities = db.Table('hotel_amenities',
    db.Column('hotel_id', db.Integer, db.ForeignKey('hotels.id'), primary_key=True),
    db.Column('amenity_id', db.Integer, db.ForeignKey('amenities.id'), primary_key=True)
)

class Hotel(db.Model):
    __tablename__ = 'hotels'
    
    id = db.Column(db.Integer, primary_key=True)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id'))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    address = db.Column(db.String(200))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))
    website = db.Column(db.String(200))
    price_range = db.Column(db.String(50))  # Budget, Mid-range, Luxury
    check_in_time = db.Column(db.String(20))
    check_out_time = db.Column(db.String(20))
    rating = db.Column(db.Float, default=0.0)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    images = db.relationship('HotelImage', backref='hotel', lazy=True, cascade='all, delete-orphan')
    amenities = db.relationship('Amenity', secondary=hotel_amenities, backref='hotels')
    rooms = db.relationship('HotelRoom', backref='hotel', lazy=True, cascade='all, delete-orphan')
    restaurant_menus = db.relationship('RestaurantMenu', backref='hotel', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('HotelReview', backref='hotel', lazy=True, cascade='all, delete-orphan')
    bookings = db.relationship('Booking', backref='hotel', lazy=True)
    
    def to_dict_basic(self):
        """Basic info for listings"""
        primary_image = next((img for img in self.images if img.is_primary), self.images[0] if self.images else None)
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description[:150] + '...' if self.description and len(self.description) > 150 else self.description,
            'address': self.address,
            'price_range': self.price_range,
            'rating': self.rating,
            'phone': self.phone,
            'primary_image': primary_image.to_dict() if primary_image else None,
            'amenities': [a.to_dict() for a in self.amenities[:3]],
            'has_restaurant': len(self.restaurant_menus) > 0,
            'destination_id': self.destination_id
        }
    
    def to_dict_detail(self):
        """Full details for single hotel view"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'address': self.address,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'phone': self.phone,
            'email': self.email,
            'website': self.website,
            'price_range': self.price_range,
            'check_in_time': self.check_in_time,
            'check_out_time': self.check_out_time,
            'rating': self.rating,
            'images': [img.to_dict() for img in self.images],
            'amenities': [a.to_dict() for a in self.amenities],
            'rooms': [room.to_dict() for room in self.rooms],
            'restaurant_menus': [menu.to_dict() for menu in self.restaurant_menus],
            'reviews': [rev.to_dict() for rev in self.reviews[:10]],
            'destination_id': self.destination_id
        }

class Amenity(db.Model):
    __tablename__ = 'amenities'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)
    icon = db.Column(db.String(50))
    
    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'icon': self.icon}

class HotelImage(db.Model):
    __tablename__ = 'hotel_images'
    
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'))
    filename = db.Column(db.String(255))
    caption = db.Column(db.String(200))
    is_primary = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'url': f'/api/uploads/{self.filename}',
            'caption': self.caption,
            'is_primary': self.is_primary
        }

class HotelRoom(db.Model):
    __tablename__ = 'hotel_rooms'
    
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'))
    name = db.Column(db.String(100))
    room_type = db.Column(db.String(50))
    description = db.Column(db.Text)
    price_per_night = db.Column(db.Float)
    currency = db.Column(db.String(10), default='KES')
    max_occupancy = db.Column(db.Integer)
    bed_type = db.Column(db.String(100))
    size_sqm = db.Column(db.Integer)
    available = db.Column(db.Boolean, default=True)
    
    # Room amenities
    has_wifi = db.Column(db.Boolean, default=False)
    has_ac = db.Column(db.Boolean, default=False)
    has_tv = db.Column(db.Boolean, default=False)
    has_minibar = db.Column(db.Boolean, default=False)
    has_safe = db.Column(db.Boolean, default=False)
    has_balcony = db.Column(db.Boolean, default=False)
    
    images = db.relationship('RoomImage', backref='room', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        primary_image = next((img for img in self.images if img.is_primary), self.images[0] if self.images else None)
        return {
            'id': self.id,
            'name': self.name,
            'room_type': self.room_type,
            'description': self.description[:100] + '...' if len(self.description) > 100 else self.description,
            'price_per_night': self.price_per_night,
            'currency': self.currency,
            'max_occupancy': self.max_occupancy,
            'bed_type': self.bed_type,
            'size_sqm': self.size_sqm,
            'primary_image': primary_image.to_dict() if primary_image else None,
            'amenities': {
                'wifi': self.has_wifi,
                'ac': self.has_ac,
                'tv': self.has_tv,
                'minibar': self.has_minibar,
                'safe': self.has_safe,
                'balcony': self.has_balcony
            }
        }

class RoomImage(db.Model):
    __tablename__ = 'room_images'
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('hotel_rooms.id'))
    filename = db.Column(db.String(255))
    caption = db.Column(db.String(200))
    is_primary = db.Column(db.Boolean, default=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'url': f'/api/uploads/{self.filename}',
            'caption': self.caption,
            'is_primary': self.is_primary
        }

class RestaurantMenu(db.Model):
    __tablename__ = 'restaurant_menus'
    
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'))
    restaurant_name = db.Column(db.String(100))
    cuisine_type = db.Column(db.String(100))
    description = db.Column(db.Text)
    opening_hours = db.Column(db.String(200))
    dress_code = db.Column(db.String(100))
    reservation_required = db.Column(db.Boolean, default=False)
    
    menu_categories = db.relationship('MenuCategory', backref='restaurant', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'restaurant_name': self.restaurant_name,
            'cuisine_type': self.cuisine_type,
            'description': self.description,
            'opening_hours': self.opening_hours,
            'dress_code': self.dress_code,
            'reservation_required': self.reservation_required,
            'menu_categories': [cat.to_dict() for cat in self.menu_categories]
        }

class MenuCategory(db.Model):
    __tablename__ = 'menu_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant_menus.id'))
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    order_index = db.Column(db.Integer, default=0)
    
    menu_items = db.relationship('MenuItem', backref='category', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'menu_items': [item.to_dict() for item in self.menu_items]
        }

class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('menu_categories.id'))
    name = db.Column(db.String(200))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    currency = db.Column(db.String(10), default='KES')
    dietary_info = db.Column(db.String(200))
    is_special = db.Column(db.Boolean, default=False)
    image = db.Column(db.String(255))
    spicy_level = db.Column(db.Integer, default=0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'currency': self.currency,
            'price_formatted': f"{self.currency} {self.price:,.2f}",
            'dietary_info': self.dietary_info.split(',') if self.dietary_info else [],
            'is_special': self.is_special,
            'image': f'/api/uploads/{self.image}' if self.image else None,
            'spicy_level': self.spicy_level
        }

class HotelReview(db.Model):
    __tablename__ = 'hotel_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    rating = db.Column(db.Float)
    comment = db.Column(db.Text)
    stay_date = db.Column(db.String(20))
    room_cleanliness = db.Column(db.Integer)
    service_rating = db.Column(db.Integer)
    value_rating = db.Column(db.Integer)
    location_rating = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_name': self.user.full_name if self.user else 'Anonymous',
            'rating': self.rating,
            'comment': self.comment,
            'stay_date': self.stay_date,
            'room_cleanliness': self.room_cleanliness,
            'service_rating': self.service_rating,
            'value_rating': self.value_rating,
            'location_rating': self.location_rating,
            'created_at': self.created_at.isoformat()
        }