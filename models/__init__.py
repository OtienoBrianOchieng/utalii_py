# models/__init__.py
from models.user import User
from models.destination import Destination, DestinationImage, DestinationVideo, Review
from models.hotel import Hotel, Amenity, HotelImage, HotelRoom, RoomImage, RestaurantMenu, MenuCategory, MenuItem, HotelReview
from models.booking import Booking, BookingStatus

# This allows importing directly from models
__all__ = [
    'User', 
    'Destination', 'DestinationImage', 'DestinationVideo', 'Review',
    'Hotel', 'Amenity', 'HotelImage', 'HotelRoom', 'RoomImage', 
    'RestaurantMenu', 'MenuCategory', 'MenuItem', 'HotelReview',
    'Booking', 'BookingStatus'
]