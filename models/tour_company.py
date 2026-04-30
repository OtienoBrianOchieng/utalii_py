# models/tour_company.py
from datetime import datetime
from models import db

class TourCompany(db.Model):
    __tablename__ = 'tour_companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    logo = db.Column(db.String(255))
    cover_image = db.Column(db.String(255))
    website = db.Column(db.String(200))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    whatsapp = db.Column(db.String(50))
    address = db.Column(db.String(200))
    
    # Social Media Handles (ADD THESE)
    facebook = db.Column(db.String(200))
    instagram = db.Column(db.String(200))
    twitter = db.Column(db.String(200))
    linkedin = db.Column(db.String(200))
    youtube = db.Column(db.String(200))
    tiktok = db.Column(db.String(200))
    
    # Contact person
    contact_person_name = db.Column(db.String(100))
    contact_person_title = db.Column(db.String(100))
    contact_person_phone = db.Column(db.String(50))
    contact_person_email = db.Column(db.String(100))
    
    # Company details
    established_year = db.Column(db.Integer)
    license_number = db.Column(db.String(100))
    insurance_info = db.Column(db.String(200))
    member_of = db.Column(db.String(200))
    
    # Service details
    service_type = db.Column(db.String(100))
    price_range = db.Column(db.String(50))
    min_price = db.Column(db.Float)
    max_price = db.Column(db.Float)
    currency = db.Column(db.String(10), default='KES')
    
    # Operating details
    languages = db.Column(db.String(200))
    group_size_min = db.Column(db.Integer, default=1)
    group_size_max = db.Column(db.Integer, default=50)
    cancellation_policy = db.Column(db.Text)
    
    # Rating and reviews
    rating = db.Column(db.Float, default=0.0)
    total_reviews = db.Column(db.Integer, default=0)
    
    # Status
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    images = db.relationship('TourCompanyImage', backref='company', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('TourCompanyReview', backref='company', lazy=True, cascade='all, delete-orphan')
    bookings = db.relationship('TourBooking', backref='company', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        """Basic company info"""
        primary_image = next((img for img in self.images if img.is_primary), self.images[0] if self.images else None)
        return {
            'id': self.id,
            'name': self.name,
            'company_name': self.company_name,
            'description': self.description[:200] + '...' if len(self.description) > 200 else self.description,
            'logo': f'/api/uploads/{self.logo}' if self.logo else None,
            'service_type': self.service_type,
            'price_range': self.price_range,
            'min_price': self.min_price,
            'max_price': self.max_price,
            'currency': self.currency,
            'rating': round(self.rating, 1),
            'total_reviews': self.total_reviews,
            'phone': self.phone,
            'email': self.email,
            'is_verified': self.is_verified,
            'facebook': self.facebook,  # Add this
            'instagram': self.instagram,  # Add this
            'twitter': self.twitter,  # Add this
            'linkedin': self.linkedin,  # Add this
            'primary_image': primary_image.to_dict() if primary_image else None
        }

    def to_dict_detail(self):
        """Detailed company info"""
        return {
            'id': self.id,
            'name': self.name,
            'company_name': self.company_name,
            'description': self.description,
            'logo': f'/api/uploads/{self.logo}' if self.logo else None,
            'cover_image': f'/api/uploads/{self.cover_image}' if self.cover_image else None,
            'website': self.website,
            'email': self.email,
            'phone': self.phone,
            'whatsapp': self.whatsapp,
            'address': self.address,
            'established_year': self.established_year,
            'license_number': self.license_number,
            'insurance_info': self.insurance_info,
            'member_of': self.member_of,
            'service_type': self.service_type,
            'price_range': self.price_range,
            'min_price': self.min_price,
            'max_price': self.max_price,
            'currency': self.currency,
            'rating': round(self.rating, 1),
            'total_reviews': self.total_reviews,
            'languages': self.languages.split(',') if self.languages else [],
            'group_size_min': self.group_size_min,
            'group_size_max': self.group_size_max,
            'cancellation_policy': self.cancellation_policy,
            'contact_person': {
                'name': self.contact_person_name,
                'title': self.contact_person_title,
                'phone': self.contact_person_phone,
                'email': self.contact_person_email
            },
            'social_media': {  # Add this section
                'facebook': self.facebook,
                'instagram': self.instagram,
                'twitter': self.twitter,
                'linkedin': self.linkedin,
                'youtube': self.youtube,
                'tiktok': self.tiktok
            },
            'images': [img.to_dict() for img in self.images],
            'reviews': [rev.to_dict() for rev in self.reviews[:10]],
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TourCompanyImage(db.Model):
    """Images for tour companies"""
    __tablename__ = 'tour_company_images'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('tour_companies.id'))
    filename = db.Column(db.String(255), nullable=False)
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


class TourCompanyReview(db.Model):
    """Reviews for tour companies"""
    __tablename__ = 'tour_company_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('tour_companies.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    booking_id = db.Column(db.Integer, db.ForeignKey('tour_bookings.id'))
    
    rating = db.Column(db.Float, nullable=False)
    comment = db.Column(db.Text)
    
    # Detailed ratings
    service_rating = db.Column(db.Float)
    value_rating = db.Column(db.Float)
    communication_rating = db.Column(db.Float)
    guide_rating = db.Column(db.Float)
    
    visit_date = db.Column(db.String(20))
    tour_taken = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_name': self.user.full_name if self.user else 'Anonymous',
            'rating': self.rating,
            'comment': self.comment,
            'service_rating': self.service_rating,
            'value_rating': self.value_rating,
            'communication_rating': self.communication_rating,
            'guide_rating': self.guide_rating,
            'tour_taken': self.tour_taken,
            'visit_date': self.visit_date,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TourBooking(db.Model):
    """Bookings for tour companies"""
    __tablename__ = 'tour_bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_reference = db.Column(db.String(50), unique=True, nullable=False)
    
    # Relationships
    company_id = db.Column(db.Integer, db.ForeignKey('tour_companies.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Booking details
    tour_name = db.Column(db.String(200))
    tour_duration = db.Column(db.String(50))
    tour_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    number_of_people = db.Column(db.Integer, nullable=False)
    
    # Pricing
    price_per_person = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='KES')
    discount = db.Column(db.Float, default=0)
    deposit_paid = db.Column(db.Float, default=0)
    balance_due = db.Column(db.Float, default=0)
    
    # Customer details
    guest_names = db.Column(db.Text)  # Comma-separated names
    special_requests = db.Column(db.Text)
    dietary_requirements = db.Column(db.Text)
    pickup_location = db.Column(db.String(200))
    dropoff_location = db.Column(db.String(200))
    
    # Contact info
    contact_name = db.Column(db.String(100))
    contact_email = db.Column(db.String(100), nullable=False)
    contact_phone = db.Column(db.String(50), nullable=False)
    emergency_contact = db.Column(db.String(100))
    
    # Payment status
    payment_status = db.Column(db.String(50), default='pending')  # pending, deposit_paid, paid, refunded
    payment_method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(100))
    
    # Booking status
    status = db.Column(db.String(50), default='pending')  # pending, confirmed, completed, cancelled, refunded
    
    # Timestamps
    booked_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Cancellation info
    cancelled_by = db.Column(db.String(50))  # user, admin, company
    cancellation_reason = db.Column(db.Text)
    refund_amount = db.Column(db.Float, default=0)
    
    def generate_booking_reference(self):
        """Generate unique booking reference"""
        import random
        import string
        prefix = "TR"
        timestamp = datetime.now().strftime('%Y%m%d')
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"{prefix}{timestamp}{random_str}"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.booking_reference:
            self.booking_reference = self.generate_booking_reference()
    
    def to_dict(self):
        return {
            'id': self.id,
            'booking_reference': self.booking_reference,
            'company_id': self.company_id,
            'company_name': self.company.name if self.company else 'N/A',
            'tour_name': self.tour_name,
            'tour_date': self.tour_date.isoformat() if self.tour_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'number_of_people': self.number_of_people,
            'price_per_person': self.price_per_person,
            'total_amount': self.total_amount,
            'currency': self.currency,
            'status': self.status,
            'payment_status': self.payment_status,
            'contact_name': self.contact_name,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'booked_at': self.booked_at.isoformat() if self.booked_at else None
        }
    
    def to_dict_detail(self):
        return {
            **self.to_dict(),
            'guest_names': self.guest_names.split(',') if self.guest_names else [],
            'special_requests': self.special_requests,
            'dietary_requirements': self.dietary_requirements,
            'pickup_location': self.pickup_location,
            'dropoff_location': self.dropoff_location,
            'emergency_contact': self.emergency_contact,
            'deposit_paid': self.deposit_paid,
            'balance_due': self.balance_due,
            'discount': self.discount,
            'payment_method': self.payment_method,
            'transaction_id': self.transaction_id,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }