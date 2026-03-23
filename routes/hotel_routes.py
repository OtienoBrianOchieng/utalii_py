# routes/hotel_routes.py
from flask import Blueprint, request, jsonify, current_app
# from models.hotel import Hotel, HotelReview, Amenity, HotelRoom
from utils.auth import token_required, optional_token
from models import db, User, Hotel, HotelReview, Amenity, HotelRoom
from sqlalchemy import func

hotel_bp = Blueprint('hotels', __name__)

@hotel_bp.route('/', methods=['GET'])
def get_hotels():
    """Get hotels with filters (public)"""
    try:
        destination_id = request.args.get('destination_id', type=int)
        price_range = request.args.get('price_range')
        min_rating = request.args.get('min_rating', type=float)
        amenity_ids = request.args.getlist('amenities[]', type=int)
        
        query = Hotel.query
        
        if destination_id:
            query = query.filter_by(destination_id=destination_id)
        if price_range:
            query = query.filter_by(price_range=price_range)
        if min_rating:
            query = query.filter(Hotel.rating >= min_rating)
        if amenity_ids:
            for amenity_id in amenity_ids:
                query = query.filter(Hotel.amenities.any(id=amenity_id))
        
        hotels = query.all()
        
        return jsonify([h.to_dict_basic() for h in hotels]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hotel_bp.route('/<int:hotel_id>', methods=['GET'])
def get_hotel(hotel_id):
    """Get single hotel details (public)"""
    try:
        hotel = Hotel.query.get_or_404(hotel_id)
        return jsonify(hotel.to_dict_detail()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hotel_bp.route('/<int:hotel_id>/rooms/available', methods=['GET'])
def check_room_availability(hotel_id):
    """Check available rooms for dates (public)"""
    try:
        from models.booking import Booking, BookingStatus
        from datetime import datetime
        
        check_in = request.args.get('check_in')
        check_out = request.args.get('check_out')
        
        if not check_in or not check_out:
            return jsonify({'error': 'Check-in and check-out dates required'}), 400
        
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        
        # Get all rooms for the hotel
        rooms = HotelRoom.query.filter_by(hotel_id=hotel_id).all()
        
        # Get bookings that conflict with these dates
        conflicting_bookings = Booking.query.filter(
            Booking.hotel_id == hotel_id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING]),
            Booking.check_out_date > check_in_date,
            Booking.check_in_date < check_out_date
        ).all()
        
        # Count booked rooms
        booked_room_ids = [b.room_id for b in conflicting_bookings if b.room_id]
        
        result = []
        for room in rooms:
            room_dict = room.to_dict()
            room_dict['available'] = room.id not in booked_room_ids
            result.append(room_dict)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@hotel_bp.route('/<int:hotel_id>/reviews', methods=['POST'])
@token_required
def add_hotel_review(current_user, hotel_id):
    """Add hotel review (authenticated users only)"""
    try:
        data = request.get_json()
        
        # Check if user already reviewed
        existing = HotelReview.query.filter_by(
            hotel_id=hotel_id, 
            user_id=current_user.id
        ).first()
        
        if existing:
            return jsonify({'error': 'You have already reviewed this hotel'}), 400
        
        # Create review
        review = HotelReview(
            hotel_id=hotel_id,
            user_id=current_user.id,
            rating=data['rating'],
            comment=data['comment'],
            stay_date=data.get('stay_date'),
            room_cleanliness=data.get('room_cleanliness', data['rating']),
            service_rating=data.get('service_rating', data['rating']),
            value_rating=data.get('value_rating', data['rating']),
            location_rating=data.get('location_rating', data['rating'])
        )
        
        db.session.add(review)
        
        # Update hotel average rating
        avg_rating = db.session.query(func.avg(HotelReview.rating)).filter_by(hotel_id=hotel_id).scalar()
        hotel = Hotel.query.get(hotel_id)
        hotel.rating = round(avg_rating, 1)
        
        db.session.commit()
        
        return jsonify(review.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@hotel_bp.route('/amenities', methods=['GET'])
def get_amenities():
    """Get all hotel amenities (public)"""
    try:
        amenities = Amenity.query.all()
        return jsonify([a.to_dict() for a in amenities]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500