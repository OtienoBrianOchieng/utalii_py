# models/__init__.py
from flask_sqlalchemy import SQLAlchemy

# Initialize db here - this will be imported by app.py
db = SQLAlchemy()

# Import all models after db is defined
from models.user import User
from models.destination import Destination, DestinationImage, DestinationVideo, Review
from models.hotel import Hotel, Amenity, HotelImage, HotelRoom, RoomImage, RestaurantMenu, MenuCategory, MenuItem, HotelReview
from models.booking import Booking, BookingStatus
from models.tour_company import (
    TourCompany, 
    TourCompanyImage, 
    TourCompanyGallery,
    TourCompanyReview, 
    TourBooking, 
    TourPackage, 
    CompanyDiscount, 
    DiscountUsage, 
    TourPackageBooking,
    CompanyDocument
)

# Export all models
__all__ = [
    'db',
    'User',
    'Destination', 'DestinationImage', 'DestinationVideo', 'Review',
    'Hotel', 'Amenity', 'HotelImage', 'HotelRoom', 'RoomImage',
    'RestaurantMenu', 'MenuCategory', 'MenuItem', 'HotelReview',
    'Booking', 'BookingStatus',
    'TourCompany', 'TourCompanyImage', 'TourCompanyGallery', 'TourCompanyReview', 
    'TourBooking', 'TourPackage', 'CompanyDiscount', 'DiscountUsage', 
    'TourPackageBooking', 'CompanyDocument'
]