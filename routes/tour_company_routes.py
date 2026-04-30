# routes/tour_company_routes.py
from flask import Blueprint, request, jsonify
from datetime import datetime, date
from utils.auth import token_required
from models import db, User, TourCompany, TourCompanyImage, TourCompanyReview, TourBooking
from sqlalchemy import func
import os
from werkzeug.utils import secure_filename

tour_bp = Blueprint('tour_companies', __name__, url_prefix='/api/tour-companies')


# ============================================================================
# PUBLIC ROUTES - No authentication required
# ============================================================================

@tour_bp.route('/', methods=['GET'])
def get_tour_companies():
    """Get all tour companies with filters"""
    try:
        service_type = request.args.get('service_type')
        price_range = request.args.get('price_range')
        min_rating = request.args.get('min_rating', type=float)
        search = request.args.get('search')
        
        query = TourCompany.query.filter_by(is_active=True, is_verified=True)
        
        if service_type:
            query = query.filter_by(service_type=service_type)
        if price_range:
            query = query.filter_by(price_range=price_range)
        if min_rating:
            query = query.filter(TourCompany.rating >= min_rating)
        if search:
            query = query.filter(
                db.or_(
                    TourCompany.name.ilike(f'%{search}%'),
                    TourCompany.company_name.ilike(f'%{search}%'),
                    TourCompany.description.ilike(f'%{search}%')
                )
            )
        
        companies = query.order_by(TourCompany.rating.desc()).all()
        return jsonify([c.to_dict() for c in companies]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/<int:company_id>', methods=['GET'])
def get_tour_company(company_id):
    """Get single tour company details"""
    try:
        company = TourCompany.query.get_or_404(company_id)
        return jsonify(company.to_dict_detail()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/service-types', methods=['GET'])
def get_service_types():
    """Get all service types"""
    try:
        types = db.session.query(TourCompany.service_type).distinct().all()
        return jsonify([t[0] for t in types if t[0]]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# AUTHENTICATED ROUTES - User must be logged in
# ============================================================================

@tour_bp.route('/<int:company_id>/reviews', methods=['POST'])
@token_required
def add_review(current_user, company_id):
    """Add review for a tour company"""
    try:
        data = request.get_json()
        
        if not data.get('rating') or not data.get('comment'):
            return jsonify({'error': 'Rating and comment required'}), 400
        
        # Check if user already reviewed
        existing = TourCompanyReview.query.filter_by(
            company_id=company_id,
            user_id=current_user.id
        ).first()
        
        if existing:
            return jsonify({'error': 'You have already reviewed this company'}), 400
        
        review = TourCompanyReview(
            company_id=company_id,
            user_id=current_user.id,
            rating=data['rating'],
            comment=data['comment'],
            service_rating=data.get('service_rating', data['rating']),
            value_rating=data.get('value_rating', data['rating']),
            communication_rating=data.get('communication_rating', data['rating']),
            guide_rating=data.get('guide_rating', data['rating']),
            tour_taken=data.get('tour_taken'),
            visit_date=data.get('visit_date')
        )
        
        db.session.add(review)
        
        # Update company rating
        avg_rating = db.session.query(func.avg(TourCompanyReview.rating)).filter_by(
            company_id=company_id
        ).scalar()
        total_reviews = TourCompanyReview.query.filter_by(company_id=company_id).count()
        
        company = TourCompany.query.get(company_id)
        company.rating = round(avg_rating, 1) if avg_rating else 0
        company.total_reviews = total_reviews
        
        db.session.commit()
        
        return jsonify(review.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/book', methods=['POST'])
@token_required
def create_booking(current_user):
    """Create a booking for a tour company"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['company_id', 'tour_date', 'number_of_people', 
                   'price_per_person', 'contact_email', 'contact_phone']
        for field in required:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Get company
        company = TourCompany.query.get(data['company_id'])
        if not company:
            return jsonify({'error': 'Tour company not found'}), 404
        
        # Validate date
        tour_date = datetime.strptime(data['tour_date'], '%Y-%m-%d').date()
        if tour_date < datetime.now().date():
            return jsonify({'error': 'Tour date cannot be in the past'}), 400
        
        # Calculate total amount
        total_amount = data['price_per_person'] * data['number_of_people']
        if data.get('discount'):
            total_amount -= data['discount']
        
        # Calculate balance due (assuming 30% deposit)
        deposit_paid = data.get('deposit_paid', total_amount * 0.3)
        balance_due = total_amount - deposit_paid
        
        # Create booking
        booking = TourBooking(
            company_id=data['company_id'],
            user_id=current_user.id,
            tour_name=data.get('tour_name'),
            tour_duration=data.get('tour_duration'),
            tour_date=tour_date,
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None,
            number_of_people=data['number_of_people'],
            price_per_person=data['price_per_person'],
            total_amount=total_amount,
            currency=data.get('currency', 'KES'),
            discount=data.get('discount', 0),
            deposit_paid=deposit_paid,
            balance_due=balance_due,
            guest_names=','.join(data.get('guest_names', [current_user.full_name])),
            special_requests=data.get('special_requests'),
            dietary_requirements=data.get('dietary_requirements'),
            pickup_location=data.get('pickup_location'),
            dropoff_location=data.get('dropoff_location'),
            contact_name=data.get('contact_name', current_user.full_name),
            contact_email=data['contact_email'],
            contact_phone=data['contact_phone'],
            emergency_contact=data.get('emergency_contact'),
            payment_method=data.get('payment_method', 'pending'),
            status='pending',
            payment_status='pending'
        )
        
        db.session.add(booking)
        db.session.commit()
        
        return jsonify({
            'message': 'Booking created successfully',
            'booking': booking.to_dict_detail()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/my-bookings', methods=['GET'])
@token_required
def get_user_bookings(current_user):
    """Get current user's tour bookings"""
    try:
        status = request.args.get('status')
        query = TourBooking.query.filter_by(user_id=current_user.id)
        
        if status:
            query = query.filter_by(status=status)
        
        bookings = query.order_by(TourBooking.booked_at.desc()).all()
        return jsonify([b.to_dict() for b in bookings]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/bookings/<int:booking_id>', methods=['GET'])
@token_required
def get_booking(current_user, booking_id):
    """Get single booking details"""
    try:
        booking = TourBooking.query.get_or_404(booking_id)
        
        if booking.user_id != current_user.id and not current_user.is_admin():
            return jsonify({'error': 'Unauthorized'}), 403
        
        return jsonify(booking.to_dict_detail()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@token_required
def cancel_booking(current_user, booking_id):
    """Cancel a booking"""
    try:
        booking = TourBooking.query.get_or_404(booking_id)
        
        if booking.user_id != current_user.id and not current_user.is_admin():
            return jsonify({'error': 'Unauthorized'}), 403
        
        if booking.status in ['cancelled', 'completed']:
            return jsonify({'error': f'Booking is already {booking.status}'}), 400
        
        data = request.get_json()
        booking.status = 'cancelled'
        booking.cancelled_at = datetime.now()
        booking.cancelled_by = 'user' if booking.user_id == current_user.id else 'admin'
        booking.cancellation_reason = data.get('reason', 'Cancelled by user')
        
        db.session.commit()
        
        return jsonify({
            'message': 'Booking cancelled successfully',
            'booking': booking.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ============================================================================
# ADMIN ROUTES
# ============================================================================

@tour_bp.route('/admin/companies', methods=['GET'])
@token_required
def get_all_companies_admin(current_user):
    """Get all companies for admin"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    companies = TourCompany.query.order_by(TourCompany.created_at.desc()).all()
    return jsonify([c.to_dict_detail() for c in companies]), 200


@tour_bp.route('/admin/companies', methods=['POST'])
@token_required
def create_company_admin(current_user):
    """Create a new tour company (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json()
        
        company = TourCompany(
            name=data['name'],
            company_name=data['company_name'],
            description=data['description'],
            service_type=data.get('service_type'),
            price_range=data.get('price_range'),
            min_price=data.get('min_price'),
            max_price=data.get('max_price'),
            currency=data.get('currency', 'KES'),
            email=data.get('email'),
            phone=data.get('phone'),
            whatsapp=data.get('whatsapp'),
            website=data.get('website'),
            address=data.get('address'),
            established_year=data.get('established_year'),
            license_number=data.get('license_number'),
            insurance_info=data.get('insurance_info'),
            member_of=data.get('member_of'),
            languages=data.get('languages'),
            group_size_min=data.get('group_size_min', 1),
            group_size_max=data.get('group_size_max', 50),
            cancellation_policy=data.get('cancellation_policy'),
            contact_person_name=data.get('contact_person_name'),
            contact_person_title=data.get('contact_person_title'),
            contact_person_phone=data.get('contact_person_phone'),
            contact_person_email=data.get('contact_person_email'),
            facebook=data.get('facebook'),
            instagram=data.get('instagram'),
            twitter=data.get('twitter'),
            is_verified=data.get('is_verified', True),
            created_by=current_user.id
        )
        
        db.session.add(company)
        db.session.commit()
        
        return jsonify(company.to_dict_detail()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/companies/<int:company_id>', methods=['PUT'])
@token_required
def update_company_admin(current_user, company_id):
    """Update a tour company (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        company = TourCompany.query.get_or_404(company_id)
        data = request.get_json()
        
        # Update fields
        for field in ['name', 'company_name', 'description', 'service_type', 'price_range',
                     'min_price', 'max_price', 'currency', 'email', 'phone', 'whatsapp',
                     'website', 'address', 'established_year', 'license_number', 'insurance_info',
                     'member_of', 'languages', 'group_size_min', 'group_size_max', 'cancellation_policy',
                     'contact_person_name', 'contact_person_title', 'contact_person_phone',
                     'contact_person_email', 'facebook', 'instagram', 'twitter']:
            if field in data:
                setattr(company, field, data[field])
        
        if 'is_verified' in data:
            company.is_verified = data['is_verified']
        if 'is_active' in data:
            company.is_active = data['is_active']
        
        db.session.commit()
        return jsonify(company.to_dict_detail()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/companies/<int:company_id>', methods=['DELETE'])
@token_required
def delete_company_admin(current_user, company_id):
    """Delete a tour company (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    company = TourCompany.query.get_or_404(company_id)
    db.session.delete(company)
    db.session.commit()
    
    return jsonify({'message': 'Company deleted successfully'}), 200


@tour_bp.route('/admin/bookings', methods=['GET'])
@token_required
def get_all_bookings_admin(current_user):
    """Get all tour bookings for admin"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    status = request.args.get('status')
    query = TourBooking.query
    
    if status:
        query = query.filter_by(status=status)
    
    bookings = query.order_by(TourBooking.booked_at.desc()).all()
    result = []
    for booking in bookings:
        booking_dict = booking.to_dict()
        user = User.query.get(booking.user_id)
        booking_dict['user_name'] = user.full_name if user else 'Unknown'
        result.append(booking_dict)
    
    return jsonify(result), 200


@tour_bp.route('/admin/bookings/<int:booking_id>/confirm', methods=['POST'])
@token_required
def confirm_booking_admin(current_user, booking_id):
    """Confirm a booking (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    booking = TourBooking.query.get_or_404(booking_id)
    
    if booking.status != 'pending':
        return jsonify({'error': f'Booking is already {booking.status}'}), 400
    
    booking.status = 'confirmed'
    booking.confirmed_at = datetime.now()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Booking confirmed successfully',
        'booking': booking.to_dict()
    }), 200


@tour_bp.route('/admin/bookings/<int:booking_id>/complete', methods=['POST'])
@token_required
def complete_booking_admin(current_user, booking_id):
    """Mark booking as completed (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    booking = TourBooking.query.get_or_404(booking_id)
    
    if booking.status != 'confirmed':
        return jsonify({'error': 'Only confirmed bookings can be completed'}), 400
    
    booking.status = 'completed'
    booking.completed_at = datetime.now()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Booking marked as completed',
        'booking': booking.to_dict()
    }), 200

# ============================================================================
# IMAGE UPLOAD ROUTES
# ============================================================================

@tour_bp.route('/admin/companies/<int:company_id>/upload-logo', methods=['POST'])
@token_required
def upload_company_logo(current_user, company_id):
    """Upload company logo (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        company = TourCompany.query.get_or_404(company_id)
        
        if 'logo' not in request.files:
            return jsonify({'error': 'No logo file provided'}), 400
        
        file = request.files['logo']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save file
        from werkzeug.utils import secure_filename
        import os
        from flask import current_app
        
        filename = secure_filename(f"company_{company_id}_logo_{file.filename}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Update company logo
        company.logo = filename
        db.session.commit()
        
        return jsonify({
            'message': 'Logo uploaded successfully',
            'logo_url': f"/api/uploads/{filename}"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/companies/<int:company_id>/upload-cover', methods=['POST'])
@token_required
def upload_company_cover(current_user, company_id):
    """Upload company cover image (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        company = TourCompany.query.get_or_404(company_id)
        
        if 'cover' not in request.files:
            return jsonify({'error': 'No cover file provided'}), 400
        
        file = request.files['cover']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        from werkzeug.utils import secure_filename
        import os
        from flask import current_app
        
        filename = secure_filename(f"company_{company_id}_cover_{file.filename}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        company.cover_image = filename
        db.session.commit()
        
        return jsonify({
            'message': 'Cover image uploaded successfully',
            'cover_url': f"/api/uploads/{filename}"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/companies/<int:company_id>/images', methods=['POST'])
@token_required
def add_company_image(current_user, company_id):
    """Add gallery image for company (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        company = TourCompany.query.get_or_404(company_id)
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        from werkzeug.utils import secure_filename
        import os
        from flask import current_app
        
        filename = secure_filename(f"company_{company_id}_img_{file.filename}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Get caption from form data
        caption = request.form.get('caption', '')
        is_primary = request.form.get('is_primary', 'false').lower() == 'true'
        
        # If this is set as primary, unset other primary images
        if is_primary:
            TourCompanyImage.query.filter_by(company_id=company_id, is_primary=True).update({'is_primary': False})
        
        company_image = TourCompanyImage(
            company_id=company_id,
            filename=filename,
            caption=caption,
            is_primary=is_primary
        )
        
        db.session.add(company_image)
        db.session.commit()
        
        return jsonify({
            'message': 'Image uploaded successfully',
            'image': company_image.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/companies/images/<int:image_id>', methods=['DELETE'])
@token_required
def delete_company_image(current_user, image_id):
    """Delete company image (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        image = TourCompanyImage.query.get_or_404(image_id)
        
        # Delete file from filesystem
        import os
        from flask import current_app
        
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], image.filename)
        if os.path.exists(filepath):
            os.remove(filepath)
        
        db.session.delete(image)
        db.session.commit()
        
        return jsonify({'message': 'Image deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/companies/images/<int:image_id>/set-primary', methods=['PUT'])
@token_required
def set_primary_image(current_user, image_id):
    """Set image as primary (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        image = TourCompanyImage.query.get_or_404(image_id)
        
        # Unset current primary images for this company
        TourCompanyImage.query.filter_by(company_id=image.company_id, is_primary=True).update({'is_primary': False})
        
        # Set this image as primary
        image.is_primary = True
        db.session.commit()
        
        return jsonify({'message': 'Primary image updated successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/companies/<int:company_id>/images', methods=['GET'])
def get_company_images(company_id):
    """Get all images for a company (public)"""
    try:
        images = TourCompanyImage.query.filter_by(company_id=company_id).all()
        return jsonify([img.to_dict() for img in images]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500