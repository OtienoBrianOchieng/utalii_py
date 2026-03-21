# models/booking.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
import enum

db = SQLAlchemy()

class BookingStatus(enum.Enum):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    CANCELLED = 'cancelled'
    COMPLETED = 'completed'

class Booking(db.Model):
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_reference = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Polymorphic - can book either a hotel room or a destination activity
    booking_type = db.Column(db.String(20), nullable=False)  # 'hotel', 'destination'
    
    # Hotel booking fields
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotels.id'), nullable=True)
    room_id = db.Column(db.Integer, db.ForeignKey('hotel_rooms.id'), nullable=True)
    check_in_date = db.Column(db.Date, nullable=True)
    check_out_date = db.Column(db.Date, nullable=True)
    number_of_rooms = db.Column(db.Integer, default=1)
    number_of_guests = db.Column(db.Integer, nullable=True)
    
    # Destination activity booking fields
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id'), nullable=True)
    activity_date = db.Column(db.Date, nullable=True)
    number_of_tickets = db.Column(db.Integer, default=1)
    
    # Common fields
    total_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='KES')
    status = db.Column(db.Enum(BookingStatus), default=BookingStatus.PENDING)
    special_requests = db.Column(db.Text)
    guest_names = db.Column(db.String(500))  # JSON string of guest names
    contact_email = db.Column(db.String(120))
    contact_phone = db.Column(db.String(20))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='bookings_list', foreign_keys=[user_id])
    hotel = db.relationship('Hotel', backref='bookings_list', foreign_keys=[hotel_id])
    room = db.relationship('HotelRoom', backref='bookings', foreign_keys=[room_id])
    destination = db.relationship('Destination', backref='bookings', foreign_keys=[destination_id])
    
    def generate_reference(self):
        """Generate unique booking reference"""
        import random
        import string
        prefix = 'KT'  # Kenya Tourism
        timestamp = datetime.now().strftime('%y%m%d')
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"{prefix}{timestamp}{random_chars}"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.booking_reference:
            self.booking_reference = self.generate_reference()
    
    def to_dict(self):
        """Basic booking info"""
        result = {
            'id': self.id,
            'booking_reference': self.booking_reference,
            'booking_type': self.booking_type,
            'status': self.status.value,
            'total_amount': self.total_amount,
            'currency': self.currency,
            'check_in_date': self.check_in_date.isoformat() if self.check_in_date else None,
            'check_out_date': self.check_out_date.isoformat() if self.check_out_date else None,
            'activity_date': self.activity_date.isoformat() if self.activity_date else None,
            'number_of_guests': self.number_of_guests,
            'number_of_tickets': self.number_of_tickets,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'special_requests': self.special_requests,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        # Add related item details
        if self.booking_type == 'hotel' and self.hotel:
            result['hotel'] = {
                'id': self.hotel.id,
                'name': self.hotel.name,
                'address': self.hotel.address
            }
            if self.room:
                result['room'] = {
                    'id': self.room.id,
                    'name': self.room.name,
                    'price_per_night': self.room.price_per_night
                }
        
        elif self.booking_type == 'destination' and self.destination:
            result['destination'] = {
                'id': self.destination.id,
                'name': self.destination.name,
                'category': self.destination.category
            }
        
        return result
    
    def to_dict_detail(self):
        """Detailed booking info for confirmation"""
        result = self.to_dict()
        result['guest_names'] = self.guest_names.split(',') if self.guest_names else []
        result['user'] = {
            'id': self.user.id,
            'full_name': self.user.full_name,
            'email': self.user.email
        } if self.user else None
        
        return result