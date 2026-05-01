# models/tour_company.py
from datetime import datetime, timedelta
from models import db

class TourCompany(db.Model):
    """Tour company/service provider model"""
    __tablename__ = 'tour_companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    logo = db.Column(db.String(255))
    cover_image = db.Column(db.String(255))
    website = db.Column(db.String(200))
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    whatsapp = db.Column(db.String(50))
    address = db.Column(db.String(200))
    
    # Social Media Handles
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
    
    # Verification and Status
    is_verified = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    verification_status = db.Column(db.String(50), default='pending')  # pending, approved, rejected, suspended
    verification_notes = db.Column(db.Text)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_at = db.Column(db.DateTime)
    
    # Application documents
    business_registration_doc = db.Column(db.String(255))  # Path to uploaded document
    tax_compliance_doc = db.Column(db.String(255))
    insurance_certificate = db.Column(db.String(255))
    license_document = db.Column(db.String(255))
    additional_documents = db.Column(db.Text)  # JSON string of additional docs
    
    # Soft delete
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime)
    deletion_requested_at = db.Column(db.DateTime)
    deletion_requested_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    deletion_scheduled_date = db.Column(db.DateTime)
    
    # Timestamps
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    images = db.relationship('TourCompanyImage', backref='company', lazy=True, cascade='all, delete-orphan')
    gallery = db.relationship('TourCompanyGallery', backref='company', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('TourCompanyReview', backref='company', lazy=True, cascade='all, delete-orphan')
    bookings = db.relationship('TourBooking', backref='company', lazy=True)
    packages = db.relationship('TourPackage', backref='company', lazy=True)
    discounts = db.relationship('CompanyDiscount', backref='company', lazy=True)
    
    def is_visible_to_users(self):
        """Check if company should be visible to regular users"""
        return self.is_verified and self.is_active and not self.is_deleted
    
    def request_deletion(self, user_id):
        """Request company deletion (scheduled for 30 days later)"""
        self.deletion_requested_at = datetime.utcnow()
        self.deletion_requested_by = user_id
        self.deletion_scheduled_date = datetime.utcnow() + timedelta(days=30)
        self.is_active = False  # Immediately hide from users
        db.session.commit()
        return self.deletion_scheduled_date
    
    def cancel_deletion_request(self):
        """Cancel pending deletion request"""
        self.deletion_requested_at = None
        self.deletion_requested_by = None
        self.deletion_scheduled_date = None
        self.is_active = True
        db.session.commit()
    
    def permanent_delete(self):
        """Permanently delete company (called after 30 days)"""
        db.session.delete(self)
        db.session.commit()
    
    @staticmethod
    def process_scheduled_deletions():
        """Process and permanently delete companies whose 30-day period has passed"""
        companies = TourCompany.query.filter(
            TourCompany.deletion_scheduled_date <= datetime.utcnow(),
            TourCompany.is_deleted == False
        ).all()
        
        for company in companies:
            company.is_deleted = True
            company.deleted_at = datetime.utcnow()
            db.session.commit()
        
        return len(companies)
    
    def to_dict(self):
        """Basic company info (public view)"""
        if not self.is_visible_to_users():
            return None
        
        primary_image = next((img for img in self.images if img.is_primary), self.images[0] if self.images else None)
        active_discounts = [d.to_dict() for d in self.discounts if d.is_active and d.is_valid()]
        
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
            'facebook': self.facebook,
            'instagram': self.instagram,
            'twitter': self.twitter,
            'linkedin': self.linkedin,
            'primary_image': primary_image.to_dict() if primary_image else None,
            'packages_count': len(self.packages),
            'gallery_count': len(self.gallery),
            'active_discounts': active_discounts,
            'active_discounts_count': len(active_discounts)
        }
    
    def to_dict_admin(self):
        """Detailed company info for admin view"""
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
            'social_media': {
                'facebook': self.facebook,
                'instagram': self.instagram,
                'twitter': self.twitter,
                'linkedin': self.linkedin,
                'youtube': self.youtube,
                'tiktok': self.tiktok
            },
            'images': [img.to_dict() for img in self.images],
            'gallery': [g.to_dict() for g in self.gallery],
            'reviews': [rev.to_dict() for rev in self.reviews[:10]],
            'packages': [pkg.to_dict() for pkg in self.packages],
            'active_discounts': [d.to_dict() for d in self.discounts if d.is_active and d.is_valid()],
            'verification_status': self.verification_status,
            'verification_notes': self.verification_notes,
            'is_verified': self.is_verified,
            'is_active': self.is_active,
            'is_deleted': self.is_deleted,
            'deletion_scheduled_date': self.deletion_scheduled_date.isoformat() if self.deletion_scheduled_date else None,
            'documents': {
                'business_registration': f'/api/uploads/{self.business_registration_doc}' if self.business_registration_doc else None,
                'tax_compliance': f'/api/uploads/{self.tax_compliance_doc}' if self.tax_compliance_doc else None,
                'insurance_certificate': f'/api/uploads/{self.insurance_certificate}' if self.insurance_certificate else None,
                'license_document': f'/api/uploads/{self.license_document}' if self.license_document else None
            },
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def to_dict_company(self):
        """Company info for the company owner view"""
        return {
            **self.to_dict_admin(),
            'deletion_requested_at': self.deletion_requested_at.isoformat() if self.deletion_requested_at else None,
            'deletion_requested_by': self.deletion_requested_by,
            'deletion_scheduled_date': self.deletion_scheduled_date.isoformat() if self.deletion_scheduled_date else None
        }


class TourCompanyImage(db.Model):
    """Images for tour companies (profile/logo images)"""
    __tablename__ = 'tour_company_images'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('tour_companies.id'), nullable=False)
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


class TourCompanyGallery(db.Model):
    """Gallery of places the company has visited (showcase their work)"""
    __tablename__ = 'tour_company_galleries'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('tour_companies.id'), nullable=False)
    
    # Image details
    image_url = db.Column(db.String(255), nullable=False)
    thumbnail_url = db.Column(db.String(255))
    caption = db.Column(db.String(200))
    description = db.Column(db.Text)
    
    # Location/place information
    location_name = db.Column(db.String(200))
    location_latitude = db.Column(db.Float)
    location_longitude = db.Column(db.Float)
    destination_id = db.Column(db.Integer, db.ForeignKey('destinations.id'))
    
    # Metadata
    taken_date = db.Column(db.Date)
    photographer = db.Column(db.String(100))
    tags = db.Column(db.String(255))
    
    # Display settings
    is_featured = db.Column(db.Boolean, default=False)
    display_order = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'image_url': f'/api/uploads/{self.image_url}' if self.image_url else None,
            'thumbnail_url': f'/api/uploads/{self.thumbnail_url}' if self.thumbnail_url else None,
            'caption': self.caption,
            'description': self.description,
            'location_name': self.location_name,
            'location_latitude': self.location_latitude,
            'location_longitude': self.location_longitude,
            'destination_id': self.destination_id,
            'taken_date': self.taken_date.isoformat() if self.taken_date else None,
            'photographer': self.photographer,
            'tags': self.tags.split(',') if self.tags else [],
            'is_featured': self.is_featured,
            'display_order': self.display_order
        }


class CompanyDocument(db.Model):
    """Documents uploaded by company for verification"""
    __tablename__ = 'company_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('tour_companies.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # registration, tax, insurance, license, other
    document_name = db.Column(db.String(200))
    file_path = db.Column(db.String(255), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_at = db.Column(db.DateTime)
    verification_notes = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')  # pending, approved, rejected
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'document_type': self.document_type,
            'document_name': self.document_name,
            'file_url': f'/api/uploads/{self.file_path}' if self.file_path else None,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'status': self.status,
            'verification_notes': self.verification_notes
        }


class CompanyDiscount(db.Model):
    """Discounts that companies can offer"""
    __tablename__ = 'company_discounts'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('tour_companies.id'), nullable=False)
    
    # Discount identification
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    discount_code = db.Column(db.String(50), unique=True, nullable=False)
    
    # Discount type
    discount_type = db.Column(db.String(50), nullable=False)
    
    # Discount values
    percentage_off = db.Column(db.Float)
    fixed_amount_off = db.Column(db.Float)
    currency = db.Column(db.String(10), default='KES')
    
    # Minimum requirements
    min_booking_value = db.Column(db.Float)
    min_number_of_people = db.Column(db.Integer)
    min_days_advance = db.Column(db.Integer)
    max_days_advance = db.Column(db.Integer)
    
    # Maximum discount limits
    max_discount_amount = db.Column(db.Float)
    max_discount_percentage = db.Column(db.Float)
    
    # Target audience
    applies_to = db.Column(db.String(50), default='all')
    
    # Specific package targeting
    specific_package_id = db.Column(db.Integer, db.ForeignKey('tour_packages.id'))
    specific_package = db.relationship('TourPackage', foreign_keys=[specific_package_id])
    
    # Date ranges
    valid_from = db.Column(db.Date, nullable=False)
    valid_to = db.Column(db.Date, nullable=False)
    
    # Usage limits
    usage_limit = db.Column(db.Integer)
    usage_count = db.Column(db.Integer, default=0)
    per_user_limit = db.Column(db.Integer, default=1)
    
    # Stacking rules
    can_stack = db.Column(db.Boolean, default=False)
    stack_priority = db.Column(db.Integer, default=0)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_public = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def is_valid(self, booking_value=None, num_people=None, days_advance=None, user=None):
        """Check if discount is currently valid"""
        today = datetime.now().date()
        
        if not (self.valid_from <= today <= self.valid_to):
            return False
        
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False
        
        if self.min_booking_value and booking_value and booking_value < self.min_booking_value:
            return False
        
        if self.min_number_of_people and num_people and num_people < self.min_number_of_people:
            return False
        
        if days_advance is not None:
            if self.min_days_advance and days_advance < self.min_days_advance:
                return False
            if self.max_days_advance and days_advance > self.max_days_advance:
                return False
        
        return True
    
    def apply_discount(self, original_price):
        """Apply discount to a price"""
        final_price = original_price
        
        if self.discount_type == 'percentage':
            discount = original_price * (self.percentage_off / 100)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            final_price = original_price - discount
        elif self.discount_type == 'fixed_amount':
            discount = self.fixed_amount_off
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            final_price = original_price - discount
        else:
            discount = original_price * (self.percentage_off / 100) if self.percentage_off else 0
            final_price = original_price - discount
        
        return max(final_price, 0)
    
    def increment_usage(self):
        """Increment discount usage count"""
        self.usage_count += 1
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'name': self.name,
            'description': self.description,
            'discount_code': self.discount_code,
            'discount_type': self.discount_type,
            'percentage_off': self.percentage_off,
            'fixed_amount_off': self.fixed_amount_off,
            'currency': self.currency,
            'min_booking_value': self.min_booking_value,
            'min_number_of_people': self.min_number_of_people,
            'min_days_advance': self.min_days_advance,
            'max_days_advance': self.max_days_advance,
            'max_discount_amount': self.max_discount_amount,
            'max_discount_percentage': self.max_discount_percentage,
            'applies_to': self.applies_to,
            'specific_package_id': self.specific_package_id,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'valid_to': self.valid_to.isoformat() if self.valid_to else None,
            'usage_limit': self.usage_limit,
            'usage_count': self.usage_count,
            'per_user_limit': self.per_user_limit,
            'can_stack': self.can_stack,
            'stack_priority': self.stack_priority,
            'is_active': self.is_active,
            'is_public': self.is_public
        }


class TourPackage(db.Model):
    """Tour packages/deals offered by tour companies"""
    __tablename__ = 'tour_packages'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('tour_companies.id'), nullable=False)
    
    # Package details
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    short_description = db.Column(db.String(300))
    
    # Package type
    package_type = db.Column(db.String(50), nullable=False)
    
    # Pricing model
    pricing_model = db.Column(db.String(50), nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='KES')
    
    # Variables for calculation
    price_per_kilometer = db.Column(db.Float)
    price_per_day = db.Column(db.Float)
    price_per_night = db.Column(db.Float)
    price_per_person = db.Column(db.Float)
    price_per_vehicle = db.Column(db.Float)
    fixed_price = db.Column(db.Float)
    
    # Package specifications
    duration_days = db.Column(db.Integer)
    duration_nights = db.Column(db.Integer)
    estimated_distance_km = db.Column(db.Float)
    
    # Capacity
    min_people = db.Column(db.Integer, default=1)
    max_people = db.Column(db.Integer, default=50)
    
    # Inclusions/Exclusions
    inclusions = db.Column(db.Text)
    exclusions = db.Column(db.Text)
    
    # Itinerary
    itinerary = db.Column(db.Text)
    
    # Media
    cover_image = db.Column(db.String(255))
    gallery_images = db.Column(db.Text)
    
    # Availability
    is_available = db.Column(db.Boolean, default=True)
    available_from = db.Column(db.Date)
    available_to = db.Column(db.Date)
    
    # Default discount
    default_discount_id = db.Column(db.Integer, db.ForeignKey('company_discounts.id'))
    default_discount = db.relationship('CompanyDiscount', foreign_keys=[default_discount_id])
    
    # Featured
    is_featured = db.Column(db.Boolean, default=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def calculate_price(self, distance=None, days=None, nights=None, people=1, vehicles=1):
        """Calculate price based on pricing model"""
        if self.pricing_model == 'per_person':
            return (self.price_per_person or self.base_price) * people
        elif self.pricing_model == 'per_vehicle':
            return (self.price_per_vehicle or self.base_price) * vehicles
        elif self.pricing_model == 'per_kilometer':
            return (self.price_per_kilometer or self.base_price) * (distance or self.estimated_distance_km or 0)
        elif self.pricing_model == 'per_day':
            return (self.price_per_day or self.base_price) * (days or self.duration_days or 1)
        elif self.pricing_model == 'per_night':
            return (self.price_per_night or self.base_price) * (nights or self.duration_nights or 1)
        elif self.pricing_model == 'fixed':
            return self.fixed_price or self.base_price
        else:
            return self.base_price
    
    def calculate_with_discount(self, discount, **kwargs):
        """Apply a specific discount to the package price"""
        original_price = self.calculate_price(**kwargs)
        return discount.apply_discount(original_price)
    
    def to_dict(self):
        return {
            'id': self.id,
            'company_id': self.company_id,
            'company_name': self.company.name if self.company else 'N/A',
            'name': self.name,
            'description': self.description,
            'short_description': self.short_description,
            'package_type': self.package_type,
            'pricing_model': self.pricing_model,
            'base_price': self.base_price,
            'currency': self.currency,
            'price_per_kilometer': self.price_per_kilometer,
            'price_per_day': self.price_per_day,
            'price_per_night': self.price_per_night,
            'price_per_person': self.price_per_person,
            'price_per_vehicle': self.price_per_vehicle,
            'fixed_price': self.fixed_price,
            'duration_days': self.duration_days,
            'duration_nights': self.duration_nights,
            'estimated_distance_km': self.estimated_distance_km,
            'min_people': self.min_people,
            'max_people': self.max_people,
            'inclusions': self.inclusions.split(',') if self.inclusions else [],
            'exclusions': self.exclusions.split(',') if self.exclusions else [],
            'itinerary': self.itinerary,
            'cover_image': f'/api/uploads/{self.cover_image}' if self.cover_image else None,
            'is_available': self.is_available,
            'available_from': self.available_from.isoformat() if self.available_from else None,
            'available_to': self.available_to.isoformat() if self.available_to else None,
            'is_featured': self.is_featured,
            'default_discount_id': self.default_discount_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class DiscountUsage(db.Model):
    """Track discount usage per user"""
    __tablename__ = 'discount_usages'
    
    id = db.Column(db.Integer, primary_key=True)
    discount_id = db.Column(db.Integer, db.ForeignKey('company_discounts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('tour_package_bookings.id'))
    used_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    discount = db.relationship('CompanyDiscount')
    
    def to_dict(self):
        return {
            'id': self.id,
            'discount_id': self.discount_id,
            'user_id': self.user_id,
            'booking_id': self.booking_id,
            'used_at': self.used_at.isoformat() if self.used_at else None
        }


class TourPackageBooking(db.Model):
    """Booking for a specific tour package with calculated costs"""
    __tablename__ = 'tour_package_bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_reference = db.Column(db.String(50), unique=True, nullable=False)
    
    # Relationships
    package_id = db.Column(db.Integer, db.ForeignKey('tour_packages.id'))
    company_id = db.Column(db.Integer, db.ForeignKey('tour_companies.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    applied_discount_id = db.Column(db.Integer, db.ForeignKey('company_discounts.id'))
    
    # Booking parameters
    distance_km = db.Column(db.Float)
    duration_days = db.Column(db.Integer)
    duration_nights = db.Column(db.Integer)
    number_of_people = db.Column(db.Integer, default=1)
    number_of_vehicles = db.Column(db.Integer, default=1)
    
    # Pricing
    original_price = db.Column(db.Float, nullable=False)
    discount_amount = db.Column(db.Float, default=0)
    discount_percentage = db.Column(db.Float, default=0)
    final_price = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='KES')
    deposit_paid = db.Column(db.Float, default=0)
    balance_due = db.Column(db.Float, default=0)
    
    # Discount details
    discount_code_used = db.Column(db.String(50))
    discount_name = db.Column(db.String(200))
    
    # Booking details
    tour_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    pickup_location = db.Column(db.String(200))
    dropoff_location = db.Column(db.String(200))
    
    # Customer details
    guest_names = db.Column(db.Text)
    special_requests = db.Column(db.Text)
    dietary_requirements = db.Column(db.Text)
    
    # Contact info
    contact_name = db.Column(db.String(100))
    contact_email = db.Column(db.String(100), nullable=False)
    contact_phone = db.Column(db.String(50), nullable=False)
    
    # Payment and status
    payment_status = db.Column(db.String(50), default='pending')
    payment_method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(100))
    status = db.Column(db.String(50), default='pending')
    
    # Timestamps
    booked_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    applied_discount = db.relationship('CompanyDiscount', foreign_keys=[applied_discount_id])
    package = db.relationship('TourPackage', foreign_keys=[package_id])
    company = db.relationship('TourCompany', foreign_keys=[company_id])
    
    def generate_booking_reference(self):
        """Generate unique booking reference"""
        import random
        import string
        prefix = "PKG"
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
            'package_id': self.package_id,
            'package_name': self.package.name if self.package else 'N/A',
            'company_name': self.company.name if self.company else 'N/A',
            'tour_date': self.tour_date.isoformat() if self.tour_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'number_of_people': self.number_of_people,
            'original_price': self.original_price,
            'discount_amount': self.discount_amount,
            'discount_percentage': self.discount_percentage,
            'discount_code_used': self.discount_code_used,
            'discount_name': self.discount_name,
            'final_price': self.final_price,
            'currency': self.currency,
            'status': self.status,
            'payment_status': self.payment_status,
            'contact_name': self.contact_name,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'booked_at': self.booked_at.isoformat() if self.booked_at else None
        }


class TourCompanyReview(db.Model):
    """Reviews for tour companies"""
    __tablename__ = 'tour_company_reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('tour_companies.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
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
    """Original bookings for tour companies"""
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
    guest_names = db.Column(db.Text)
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
    payment_status = db.Column(db.String(50), default='pending')
    payment_method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(100))
    
    # Booking status
    status = db.Column(db.String(50), default='pending')
    
    # Timestamps
    booked_at = db.Column(db.DateTime, default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    # Cancellation info
    cancelled_by = db.Column(db.String(50))
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