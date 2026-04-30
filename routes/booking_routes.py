# routes/booking_routes.py
from flask import Blueprint, request, jsonify, current_app
# from models.booking import Booking, BookingStatus
# from models.user import User
# from models.hotel import Hotel, HotelRoom
# from models.destination import Destination
from utils.auth import token_required
from models import db, User, Hotel, HotelRoom, Destination, Booking, BookingStatus
from datetime import datetime, timedelta
import json

booking_bp = Blueprint('bookings', __name__)

@booking_bp.route('/', methods=['GET'])
@token_required
def get_user_bookings(current_user):
    """Get all bookings for current user"""
    try:
        status = request.args.get('status')
        
        query = Booking.query.filter_by(user_id=current_user.id)
        
        if status:
            query = query.filter_by(status=BookingStatus(status))
        
        bookings = query.order_by(Booking.created_at.desc()).all()
        
        return jsonify([b.to_dict() for b in bookings]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/<int:booking_id>', methods=['GET'])
@token_required
def get_booking(current_user, booking_id):
    """Get single booking details"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check if booking belongs to user or user is admin
        if booking.user_id != current_user.id and not current_user.is_admin():
            return jsonify({'error': 'Unauthorized'}), 403
        
        return jsonify(booking.to_dict_detail()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/hotel', methods=['POST'])
@token_required
def create_hotel_booking(current_user):
    """Create a new hotel booking"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['hotel_id', 'room_id', 'check_in_date', 'check_out_date', 
                   'number_of_guests', 'contact_email', 'contact_phone']
        for field in required:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Get hotel and room
        hotel = Hotel.query.get(data['hotel_id'])
        if not hotel:
            return jsonify({'error': 'Hotel not found'}), 404
        
        room = HotelRoom.query.get(data['room_id'])
        if not room or room.hotel_id != hotel.id:
            return jsonify({'error': 'Room not found'}), 404
        
        # Parse dates
        check_in = datetime.strptime(data['check_in_date'], '%Y-%m-%d').date()
        check_out = datetime.strptime(data['check_out_date'], '%Y-%m-%d').date()
        
        # Validate dates
        if check_in >= check_out:
            return jsonify({'error': 'Check-out date must be after check-in date'}), 400
        
        if check_in < datetime.now().date():
            return jsonify({'error': 'Check-in date cannot be in the past'}), 400
        
        # Check availability
        conflicting = Booking.query.filter(
            Booking.hotel_id == hotel.id,
            Booking.room_id == room.id,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING]),
            Booking.check_out_date > check_in,
            Booking.check_in_date < check_out
        ).first()
        
        if conflicting:
            return jsonify({'error': 'Room is not available for selected dates'}), 400
        
        # Calculate total amount
        nights = (check_out - check_in).days
        total_amount = room.price_per_night * nights * data.get('number_of_rooms', 1)
        
        # Create booking
        booking = Booking(
            user_id=current_user.id,
            booking_type='hotel',
            hotel_id=hotel.id,
            room_id=room.id,
            check_in_date=check_in,
            check_out_date=check_out,
            number_of_rooms=data.get('number_of_rooms', 1),
            number_of_guests=data['number_of_guests'],
            total_amount=total_amount,
            currency=room.currency,
            status=BookingStatus.PENDING,
            special_requests=data.get('special_requests'),
            guest_names=','.join(data.get('guest_names', [current_user.full_name])),
            contact_email=data['contact_email'],
            contact_phone=data['contact_phone']
        )
        
        db.session.add(booking)
        db.session.commit()
        
        # TODO: Send confirmation email
        
        return jsonify({
            'message': 'Booking created successfully',
            'booking': booking.to_dict_detail()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/destination', methods=['POST'])
@token_required
def create_destination_booking(current_user):
    """Create a new destination activity booking"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['destination_id', 'activity_date', 'number_of_tickets', 
                   'total_amount', 'contact_email', 'contact_phone']
        for field in required:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Get destination
        destination = Destination.query.get(data['destination_id'])
        if not destination:
            return jsonify({'error': 'Destination not found'}), 404
        
        # Parse date
        activity_date = datetime.strptime(data['activity_date'], '%Y-%m-%d').date()
        
        # Validate date
        if activity_date < datetime.now().date():
            return jsonify({'error': 'Activity date cannot be in the past'}), 400
        
        # Create booking
        booking = Booking(
            user_id=current_user.id,
            booking_type='destination',
            destination_id=destination.id,
            activity_date=activity_date,
            number_of_tickets=data['number_of_tickets'],
            total_amount=data['total_amount'],
            currency=data.get('currency', 'KES'),
            status=BookingStatus.PENDING,
            special_requests=data.get('special_requests'),
            guest_names=','.join(data.get('guest_names', [current_user.full_name])),
            contact_email=data['contact_email'],
            contact_phone=data['contact_phone']
        )
        
        db.session.add(booking)
        db.session.commit()
        
        # TODO: Send confirmation email
        
        return jsonify({
            'message': 'Booking created successfully',
            'booking': booking.to_dict_detail()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/<int:booking_id>/cancel', methods=['POST'])
@token_required
def cancel_booking(current_user, booking_id):
    """Cancel a booking"""
    try:
        booking = Booking.query.get_or_404(booking_id)
        
        # Check if booking belongs to user
        if booking.user_id != current_user.id and not current_user.is_admin():
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Check if booking can be cancelled
        if booking.status in [BookingStatus.CANCELLED, BookingStatus.COMPLETED]:
            return jsonify({'error': f'Booking is already {booking.status.value}'}), 400
        
        # Update status
        booking.status = BookingStatus.CANCELLED
        db.session.commit()
        
        # TODO: Send cancellation email
        
        return jsonify({
            'message': 'Booking cancelled successfully',
            'booking': booking.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@booking_bp.route('/<int:booking_id>/confirm', methods=['POST'])
@token_required
def confirm_booking(current_user, booking_id):
    """Confirm a booking (admin only - or auto-confirm after payment)"""
    try:
        # This would typically be called after payment is processed
        # For now, we'll allow admins to confirm
        
        if not current_user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        booking = Booking.query.get_or_404(booking_id)
        
        if booking.status != BookingStatus.PENDING:
            return jsonify({'error': f'Booking is already {booking.status.value}'}), 400
        
        booking.status = BookingStatus.CONFIRMED
        db.session.commit()
        
        # TODO: Send confirmation email
        
        return jsonify({
            'message': 'Booking confirmed successfully',
            'booking': booking.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Add to booking_routes.py

@booking_bp.route('/admin/all', methods=['GET'])
@token_required
def get_all_bookings_admin(current_user):
    """Get all bookings for admin (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    status_filter = request.args.get('status')
    query = Booking.query
    
    if status_filter:
        query = query.filter_by(status=BookingStatus(status_filter))
    
    bookings = query.order_by(Booking.created_at.desc()).all()
    return jsonify([b.to_dict() for b in bookings]), 200