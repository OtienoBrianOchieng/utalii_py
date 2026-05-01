# routes/tour_company_routes.py
from flask import Blueprint, request, jsonify
from datetime import datetime, date, timedelta
from utils.auth import token_required
from models import db, User, TourCompany, TourCompanyImage, TourCompanyGallery, TourCompanyReview, TourBooking, TourPackage, CompanyDiscount, DiscountUsage, TourPackageBooking, CompanyDocument
from sqlalchemy import func, or_
import os
import json
from werkzeug.utils import secure_filename
from flask import current_app

tour_bp = Blueprint('tour_companies', __name__, url_prefix='/api/tour-companies')


@tour_bp.route('/', methods=['GET'])
def get_tour_companies():
    """Get all tour companies with filters (only verified and active)"""
    try:
        print("=" * 50)
        print("DEBUG: get_tour_companies called")
        print("=" * 50)
        
        service_type = request.args.get('service_type')
        price_range = request.args.get('price_range')
        min_rating = request.args.get('min_rating', type=float)
        search = request.args.get('search')
        
        print(f"Filters: service_type={service_type}, price_range={price_range}, min_rating={min_rating}, search={search}")
        
        query = TourCompany.query.filter(
            TourCompany.is_verified == True,
            TourCompany.is_active == True,
            TourCompany.is_deleted == False
        )
        
        if service_type:
            query = query.filter_by(service_type=service_type)
        if price_range:
            query = query.filter_by(price_range=price_range)
        if min_rating:
            query = query.filter(TourCompany.rating >= min_rating)
        if search:
            query = query.filter(
                or_(
                    TourCompany.name.ilike(f'%{search}%'),
                    TourCompany.company_name.ilike(f'%{search}%'),
                    TourCompany.description.ilike(f'%{search}%')
                )
            )
        
        print("Executing query...")
        companies = query.order_by(TourCompany.rating.desc()).all()
        print(f"Found {len(companies)} companies")
        
        print("Converting to dict...")
        result = []
        for idx, c in enumerate(companies):
            print(f"  Processing company {idx+1}: {c.name}")
            try:
                c_dict = c.to_dict()
                if c_dict is not None:
                    result.append(c_dict)
                    print(f"    Success! Has discount: {c_dict.get('active_discounts_count', 0) > 0}")
                else:
                    print(f"    Company returned None (not visible)")
            except Exception as e:
                print(f"    ERROR converting company {c.name}: {str(e)}")
                import traceback
                traceback.print_exc()
                raise
        
        print(f"Successfully converted {len(result)} companies")
        print("Returning JSON response")
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"ERROR in get_tour_companies: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@tour_bp.route('/<int:company_id>', methods=['GET'])
def get_tour_company(company_id):
    """Get single tour company details (only if verified and active)"""
    try:
        company = TourCompany.query.get_or_404(company_id)
        
        if not company.is_visible_to_users():
            return jsonify({'error': 'Company not available'}), 404
            
        return jsonify(company.to_dict_admin()), 200
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


@tour_bp.route('/packages', methods=['GET'])
def get_all_packages():
    """Get all available tour packages with filters"""
    try:
        package_type = request.args.get('package_type')
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        search = request.args.get('search')
        
        query = TourPackage.query.join(TourCompany).filter(
            TourPackage.is_available == True,
            TourCompany.is_verified == True,
            TourCompany.is_active == True,
            TourCompany.is_deleted == False
        )
        
        if package_type:
            query = query.filter_by(package_type=package_type)
        if min_price:
            query = query.filter(TourPackage.base_price >= min_price)
        if max_price:
            query = query.filter(TourPackage.base_price <= max_price)
        if search:
            query = query.filter(
                or_(
                    TourPackage.name.ilike(f'%{search}%'),
                    TourPackage.description.ilike(f'%{search}%')
                )
            )
        
        packages = query.order_by(TourPackage.created_at.desc()).all()
        return jsonify([pkg.to_dict() for pkg in packages]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/packages/<int:package_id>', methods=['GET'])
def get_package(package_id):
    """Get single package details"""
    try:
        package = TourPackage.query.get_or_404(package_id)
        company = TourCompany.query.get(package.company_id)
        
        if not company.is_visible_to_users():
            return jsonify({'error': 'Package not available'}), 404
            
        return jsonify(package.to_dict()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/packages/<int:package_id>/calculate', methods=['POST'])
def calculate_package_price(package_id):
    """Calculate price for a package based on user inputs"""
    try:
        package = TourPackage.query.get_or_404(package_id)
        data = request.get_json()
        
        distance = data.get('distance_km')
        days = data.get('duration_days')
        nights = data.get('duration_nights')
        people = data.get('number_of_people', 1)
        vehicles = data.get('number_of_vehicles', 1)
        
        original_price = package.calculate_price(
            distance=distance,
            days=days,
            nights=nights,
            people=people,
            vehicles=vehicles
        )
        
        discount_code = data.get('discount_code')
        discount = None
        discounted_price = original_price
        
        if discount_code:
            discount = CompanyDiscount.query.filter_by(
                discount_code=discount_code.upper(),
                is_active=True
            ).first()
            
            if discount and discount.is_valid(
                booking_value=original_price,
                num_people=people,
                days_advance=(datetime.strptime(data.get('tour_date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date() - datetime.now().date()).days if data.get('tour_date') else None
            ):
                discounted_price = discount.apply_discount(original_price)
        
        return jsonify({
            'package': package.to_dict(),
            'calculation_params': {
                'distance_km': distance,
                'duration_days': days,
                'duration_nights': nights,
                'number_of_people': people,
                'number_of_vehicles': vehicles
            },
            'original_price': original_price,
            'discount_applied': discount.to_dict() if discount else None,
            'final_price': discounted_price,
            'currency': package.currency,
            'savings': original_price - discounted_price
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/discounts/validate', methods=['POST'])
def validate_discount_code():
    """Validate a discount code"""
    try:
        data = request.get_json()
        discount_code = data.get('discount_code')
        booking_value = data.get('booking_value')
        num_people = data.get('number_of_people')
        days_advance = data.get('days_advance')
        
        discount = CompanyDiscount.query.filter_by(
            discount_code=discount_code.upper(),
            is_active=True
        ).first()
        
        if not discount:
            return jsonify({'valid': False, 'message': 'Invalid discount code'}), 404
        
        if not discount.is_valid(
            booking_value=booking_value,
            num_people=num_people,
            days_advance=days_advance
        ):
            return jsonify({'valid': False, 'message': 'Discount code is not applicable'}), 400
        
        return jsonify({
            'valid': True,
            'discount': discount.to_dict(),
            'applied_discount': discount.apply_discount(booking_value) if booking_value else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/<int:company_id>/gallery', methods=['GET'])
def get_company_gallery(company_id):
    """Get all gallery images for a company"""
    try:
        company = TourCompany.query.get_or_404(company_id)
        
        if not company.is_visible_to_users():
            return jsonify({'error': 'Gallery not available'}), 404
            
        gallery = TourCompanyGallery.query.filter_by(company_id=company_id).order_by(
            TourCompanyGallery.display_order,
            TourCompanyGallery.created_at.desc()
        ).all()
        return jsonify([g.to_dict() for g in gallery]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/<int:company_id>/reviews', methods=['POST'])
@token_required
def add_review(current_user, company_id):
    """Add review for a tour company"""
    try:
        data = request.get_json()
        
        if not data.get('rating') or not data.get('comment'):
            return jsonify({'error': 'Rating and comment required'}), 400
        
        company = TourCompany.query.get_or_404(company_id)
        
        if not company.is_visible_to_users():
            return jsonify({'error': 'Cannot review this company'}), 404
        
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
        
        avg_rating = db.session.query(func.avg(TourCompanyReview.rating)).filter_by(
            company_id=company_id
        ).scalar()
        total_reviews = TourCompanyReview.query.filter_by(company_id=company_id).count()
        
        company.rating = round(avg_rating, 1) if avg_rating else 0
        company.total_reviews = total_reviews
        
        db.session.commit()
        
        return jsonify(review.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/packages/book', methods=['POST'])
@token_required
def book_package(current_user):
    """Book a tour package with calculated pricing"""
    try:
        data = request.get_json()
        
        required = ['package_id', 'tour_date', 'number_of_people', 'contact_email', 'contact_phone']
        for field in required:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        package = TourPackage.query.get_or_404(data['package_id'])
        company = TourCompany.query.get_or_404(package.company_id)
        
        if not company.is_visible_to_users():
            return jsonify({'error': 'Company not available'}), 404
        
        tour_date = datetime.strptime(data['tour_date'], '%Y-%m-%d').date()
        if tour_date < datetime.now().date():
            return jsonify({'error': 'Tour date cannot be in the past'}), 400
        
        original_price = package.calculate_price(
            distance=data.get('distance_km'),
            days=data.get('duration_days'),
            nights=data.get('duration_nights'),
            people=data['number_of_people'],
            vehicles=data.get('number_of_vehicles', 1)
        )
        
        discount_amount = 0
        discount_percentage = 0
        discount_code_used = None
        discount_name = None
        applied_discount_id = None
        final_price = original_price
        
        if data.get('discount_code'):
            discount = CompanyDiscount.query.filter_by(
                discount_code=data['discount_code'].upper(),
                is_active=True
            ).first()
            
            if discount and discount.is_valid(
                booking_value=original_price,
                num_people=data['number_of_people'],
                days_advance=(tour_date - datetime.now().date()).days
            ):
                final_price = discount.apply_discount(original_price)
                discount_amount = original_price - final_price
                discount_percentage = discount.percentage_off or 0
                discount_code_used = discount.discount_code
                discount_name = discount.name
                applied_discount_id = discount.id
                
                discount.increment_usage()
                
                usage = DiscountUsage(
                    discount_id=discount.id,
                    user_id=current_user.id
                )
                db.session.add(usage)
        
        deposit_percentage = data.get('deposit_percentage', 30)
        deposit_paid = final_price * (deposit_percentage / 100)
        balance_due = final_price - deposit_paid
        
        booking = TourPackageBooking(
            package_id=package.id,
            company_id=company.id,
            user_id=current_user.id,
            applied_discount_id=applied_discount_id,
            distance_km=data.get('distance_km'),
            duration_days=data.get('duration_days'),
            duration_nights=data.get('duration_nights'),
            number_of_people=data['number_of_people'],
            number_of_vehicles=data.get('number_of_vehicles', 1),
            original_price=original_price,
            discount_amount=discount_amount,
            discount_percentage=discount_percentage,
            discount_code_used=discount_code_used,
            discount_name=discount_name,
            final_price=final_price,
            currency=package.currency,
            deposit_paid=deposit_paid,
            balance_due=balance_due,
            tour_date=tour_date,
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None,
            pickup_location=data.get('pickup_location'),
            dropoff_location=data.get('dropoff_location'),
            guest_names=','.join(data.get('guest_names', [current_user.full_name])),
            special_requests=data.get('special_requests'),
            dietary_requirements=data.get('dietary_requirements'),
            contact_name=data.get('contact_name', current_user.full_name),
            contact_email=data['contact_email'],
            contact_phone=data['contact_phone'],
            payment_method=data.get('payment_method', 'pending'),
            status='pending',
            payment_status='pending'
        )
        
        db.session.add(booking)
        db.session.commit()
        
        return jsonify({
            'message': 'Package booked successfully',
            'booking': booking.to_dict(),
            'price_breakdown': {
                'original_price': original_price,
                'discount_amount': discount_amount,
                'discount_percentage': discount_percentage,
                'final_price': final_price,
                'deposit_paid': deposit_paid,
                'balance_due': balance_due,
                'currency': package.currency
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/my-package-bookings', methods=['GET'])
@token_required
def get_user_package_bookings(current_user):
    """Get current user's package bookings"""
    try:
        status = request.args.get('status')
        query = TourPackageBooking.query.filter_by(user_id=current_user.id)
        
        if status:
            query = query.filter_by(status=status)
        
        bookings = query.order_by(TourPackageBooking.booked_at.desc()).all()
        return jsonify([b.to_dict() for b in bookings]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/my-company', methods=['GET'])
@token_required
def get_my_company(current_user):
    """Get the company owned by the current user (company owner)"""
    try:
        company = TourCompany.query.filter_by(created_by=current_user.id).first()
        
        if not company:
            return jsonify({'error': 'You do not own a company'}), 404
        
        return jsonify(company.to_dict_company()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/my-company', methods=['PUT'])
@token_required
def update_my_company(current_user):
    """Update company information (company owner)"""
    try:
        company = TourCompany.query.filter_by(created_by=current_user.id).first()
        
        if not company:
            return jsonify({'error': 'You do not own a company'}), 404
        
        if company.deletion_scheduled_date:
            return jsonify({'error': 'Company is scheduled for deletion. Cannot update.'}), 400
        
        data = request.get_json()
        
        allowed_fields = ['description', 'service_type', 'price_range', 'min_price', 'max_price',
                         'whatsapp', 'website', 'address', 'languages', 'group_size_min', 
                         'group_size_max', 'cancellation_policy', 'facebook', 'instagram', 
                         'twitter', 'linkedin', 'youtube', 'tiktok']
        
        for field in allowed_fields:
            if field in data:
                setattr(company, field, data[field])
        
        db.session.commit()
        
        return jsonify({
            'message': 'Company updated successfully',
            'company': company.to_dict_company()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/my-company/request-deletion', methods=['POST'])
@token_required
def request_company_deletion(current_user):
    """Request deletion of company (30-day scheduled deletion)"""
    try:
        company = TourCompany.query.filter_by(created_by=current_user.id).first()
        
        if not company:
            return jsonify({'error': 'You do not own a company'}), 404
        
        if company.deletion_scheduled_date:
            return jsonify({'error': 'Deletion already requested'}), 400
        
        scheduled_date = company.request_deletion(current_user.id)
        
        return jsonify({
            'message': 'Deletion requested. Company will be permanently deleted after 30 days.',
            'scheduled_deletion_date': scheduled_date.isoformat(),
            'cancellation_available': True
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/my-company/cancel-deletion', methods=['POST'])
@token_required
def cancel_company_deletion(current_user):
    """Cancel pending deletion request"""
    try:
        company = TourCompany.query.filter_by(created_by=current_user.id).first()
        
        if not company:
            return jsonify({'error': 'You do not own a company'}), 404
        
        if not company.deletion_scheduled_date:
            return jsonify({'error': 'No pending deletion request'}), 400
        
        company.cancel_deletion_request()
        
        return jsonify({
            'message': 'Deletion request cancelled. Company is active again.',
            'company': company.to_dict_company()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/my-company/documents', methods=['POST'])
@token_required
def upload_company_document(current_user):
    """Upload verification document (company owner)"""
    try:
        company = TourCompany.query.filter_by(created_by=current_user.id).first()
        
        if not company:
            return jsonify({'error': 'You do not own a company'}), 404
        
        if 'document' not in request.files:
            return jsonify({'error': 'No document file provided'}), 400
        
        file = request.files['document']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        document_type = request.form.get('document_type')
        if not document_type:
            return jsonify({'error': 'Document type is required'}), 400
        
        filename = secure_filename(f"company_{company.id}_{document_type}_{file.filename}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        doc = CompanyDocument(
            company_id=company.id,
            document_type=document_type,
            document_name=request.form.get('document_name', document_type),
            file_path=filename,
            uploaded_by=current_user.id,
            status='pending'
        )
        
        db.session.add(doc)
        db.session.commit()
        
        return jsonify({
            'message': 'Document uploaded successfully',
            'document': doc.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/my-company/documents', methods=['GET'])
@token_required
def get_my_company_documents(current_user):
    """Get all documents for my company"""
    try:
        company = TourCompany.query.filter_by(created_by=current_user.id).first()
        
        if not company:
            return jsonify({'error': 'You do not own a company'}), 404
        
        documents = CompanyDocument.query.filter_by(company_id=company.id).all()
        return jsonify([doc.to_dict() for doc in documents]), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/companies', methods=['GET'])
@token_required
def get_all_companies_admin(current_user):
    """Get all companies for admin (including pending, inactive, etc.)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    verification_status = request.args.get('verification_status')
    query = TourCompany.query
    
    if verification_status:
        query = query.filter_by(verification_status=verification_status)
    
    companies = query.order_by(TourCompany.created_at.desc()).all()
    return jsonify([c.to_dict_admin() for c in companies]), 200


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
            linkedin=data.get('linkedin'),
            youtube=data.get('youtube'),
            tiktok=data.get('tiktok'),
            is_verified=data.get('is_verified', True),
            is_active=data.get('is_active', True),
            verification_status='approved' if data.get('is_verified', True) else 'pending',
            created_by=current_user.id
        )
        
        db.session.add(company)
        db.session.commit()
        
        return jsonify(company.to_dict_admin()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Add this to your tour_company_routes.py - PUBLIC REGISTRATION (no token required)

@tour_bp.route('/register', methods=['POST'])
def company_register_company():
    """Public company registration - no authentication required"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['name', 'company_name', 'description', 'email', 'phone', 
                   'contact_person_name', 'contact_person_phone', 'agreed_to_policy']
        for field in required:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if company with same email already exists
        existing = TourCompany.query.filter_by(email=data['email']).first()
        if existing:
            return jsonify({'error': 'A company with this email already exists'}), 400
        
        # Create company (not verified, not active until admin approval)
        company = TourCompany(
            name=data['name'],
            company_name=data['company_name'],
            description=data['description'],
            service_type=data.get('service_type'),
            price_range=data.get('price_range'),
            min_price=data.get('min_price'),
            max_price=data.get('max_price'),
            currency=data.get('currency', 'KES'),
            email=data['email'],
            phone=data['phone'],
            whatsapp=data.get('whatsapp'),
            website=data.get('website'),
            address=data.get('address'),
            languages=data.get('languages'),
            group_size_min=data.get('group_size_min', 1),
            group_size_max=data.get('group_size_max', 50),
            cancellation_policy=data.get('cancellation_policy'),
            contact_person_name=data['contact_person_name'],
            contact_person_title=data.get('contact_person_title'),
            contact_person_phone=data['contact_person_phone'],
            contact_person_email=data.get('contact_person_email'),
            facebook=data.get('facebook'),
            instagram=data.get('instagram'),
            twitter=data.get('twitter'),
            linkedin=data.get('linkedin'),
            youtube=data.get('youtube'),
            tiktok=data.get('tiktok'),
            is_verified=False,
            is_active=False,
            verification_status='pending',
            created_by=None
        )
        
        db.session.add(company)
        db.session.flush()  # Get company ID without committing
        
        # Handle document uploads if provided (base64 or URLs)
        # For file uploads, you'd handle multipart form data separately
        # This is a simplified version for JSON registration
        
        db.session.commit()
        
        return jsonify({
            'message': 'Company registration submitted successfully. Awaiting admin verification.',
            'company_id': company.id,
            'verification_status': 'pending'
        }), 201
        
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
        
        update_fields = ['name', 'company_name', 'description', 'service_type', 'price_range',
                        'min_price', 'max_price', 'currency', 'email', 'phone', 'whatsapp',
                        'website', 'address', 'established_year', 'license_number', 'insurance_info',
                        'member_of', 'languages', 'group_size_min', 'group_size_max', 'cancellation_policy',
                        'contact_person_name', 'contact_person_title', 'contact_person_phone',
                        'contact_person_email', 'facebook', 'instagram', 'twitter', 'linkedin', 
                        'youtube', 'tiktok']
        
        for field in update_fields:
            if field in data:
                setattr(company, field, data[field])
        
        if 'is_verified' in data:
            company.is_verified = data['is_verified']
            company.verification_status = 'approved' if data['is_verified'] else 'rejected'
            if data['is_verified']:
                company.verified_by = current_user.id
                company.verified_at = datetime.utcnow()
        
        if 'is_active' in data:
            company.is_active = data['is_active']
        
        db.session.commit()
        return jsonify(company.to_dict_admin()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/companies/<int:company_id>/verify', methods=['POST'])
@token_required
def verify_company_admin(current_user, company_id):
    """Verify or reject a company application (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        company = TourCompany.query.get_or_404(company_id)
        data = request.get_json()
        
        action = data.get('action')
        notes = data.get('notes', '')
        
        if action == 'approve':
            company.is_verified = True
            company.is_active = True
            company.verification_status = 'approved'
            company.verified_by = current_user.id
            company.verified_at = datetime.utcnow()
            message = 'Company approved and activated successfully'
        elif action == 'reject':
            company.is_verified = False
            company.is_active = False
            company.verification_status = 'rejected'
            message = 'Company application rejected'
        elif action == 'suspend':
            company.is_active = False
            company.verification_status = 'suspended'
            message = 'Company suspended'
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
        if notes:
            company.verification_notes = notes
        
        db.session.commit()
        
        return jsonify({
            'message': message,
            'company': company.to_dict_admin()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/companies/<int:company_id>/activate', methods=['POST'])
@token_required
def activate_company_admin(current_user, company_id):
    """Activate a company (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        company = TourCompany.query.get_or_404(company_id)
        
        if not company.is_verified:
            return jsonify({'error': 'Cannot activate unverified company'}), 400
        
        company.is_active = True
        db.session.commit()
        
        return jsonify({
            'message': 'Company activated successfully',
            'company': company.to_dict_admin()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/companies/<int:company_id>/deactivate', methods=['POST'])
@token_required
def deactivate_company_admin(current_user, company_id):
    """Deactivate a company (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        company = TourCompany.query.get_or_404(company_id)
        company.is_active = False
        db.session.commit()
        
        return jsonify({
            'message': 'Company deactivated successfully',
            'company': company.to_dict_admin()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/companies/<int:company_id>/permanent-delete', methods=['DELETE'])
@token_required
def permanent_delete_company_admin(current_user, company_id):
    """Permanently delete a company (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        company = TourCompany.query.get_or_404(company_id)
        
        if company.deletion_scheduled_date:
            if datetime.utcnow().date() < company.deletion_scheduled_date.date():
                return jsonify({
                    'error': f'Cannot delete yet. Scheduled for {company.deletion_scheduled_date.date()}',
                    'days_remaining': (company.deletion_scheduled_date.date() - datetime.utcnow().date()).days
                }), 400
        
        if company.logo:
            logo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], company.logo)
            if os.path.exists(logo_path):
                os.remove(logo_path)
        
        if company.cover_image:
            cover_path = os.path.join(current_app.config['UPLOAD_FOLDER'], company.cover_image)
            if os.path.exists(cover_path):
                os.remove(cover_path)
        
        company.permanent_delete()
        
        return jsonify({'message': 'Company permanently deleted'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/companies/<int:company_id>/documents', methods=['GET'])
@token_required
def get_company_documents_admin(current_user, company_id):
    """Get all documents for a company (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    documents = CompanyDocument.query.filter_by(company_id=company_id).all()
    return jsonify([doc.to_dict() for doc in documents]), 200


@tour_bp.route('/admin/documents/<int:document_id>/verify', methods=['POST'])
@token_required
def verify_document_admin(current_user, document_id):
    """Verify or reject a document (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        doc = CompanyDocument.query.get_or_404(document_id)
        data = request.get_json()
        
        status = data.get('status')
        notes = data.get('notes', '')
        
        if status not in ['approved', 'rejected']:
            return jsonify({'error': 'Invalid status'}), 400
        
        doc.status = status
        doc.verification_notes = notes
        doc.verified_by = current_user.id
        doc.verified_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': f'Document {status}',
            'document': doc.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/process-scheduled-deletions', methods=['POST'])
@token_required
def process_scheduled_deletions(current_user):
    """Process and permanently delete companies whose 30-day period has passed (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        count = TourCompany.process_scheduled_deletions()
        
        return jsonify({
            'message': f'Processed {count} scheduled deletions',
            'deleted_count': count
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


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


@tour_bp.route('/admin/package-bookings', methods=['GET'])
@token_required
def get_all_package_bookings_admin(current_user):
    """Get all package bookings for admin"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    status = request.args.get('status')
    query = TourPackageBooking.query
    
    if status:
        query = query.filter_by(status=status)
    
    bookings = query.order_by(TourPackageBooking.booked_at.desc()).all()
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


@tour_bp.route('/admin/package-bookings/<int:booking_id>/confirm', methods=['POST'])
@token_required
def confirm_package_booking_admin(current_user, booking_id):
    """Confirm a package booking (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    booking = TourPackageBooking.query.get_or_404(booking_id)
    
    if booking.status != 'pending':
        return jsonify({'error': f'Booking is already {booking.status}'}), 400
    
    booking.status = 'confirmed'
    booking.confirmed_at = datetime.now()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Package booking confirmed successfully',
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


@tour_bp.route('/admin/package-bookings/<int:booking_id>/complete', methods=['POST'])
@token_required
def complete_package_booking_admin(current_user, booking_id):
    """Mark package booking as completed (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    booking = TourPackageBooking.query.get_or_404(booking_id)
    
    if booking.status != 'confirmed':
        return jsonify({'error': 'Only confirmed bookings can be completed'}), 400
    
    booking.status = 'completed'
    booking.completed_at = datetime.now()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Package booking marked as completed',
        'booking': booking.to_dict()
    }), 200


@tour_bp.route('/admin/companies/<int:company_id>/packages', methods=['GET'])
@token_required
def get_company_packages_admin(current_user, company_id):
    """Get all packages for a company (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    packages = TourPackage.query.filter_by(company_id=company_id).order_by(TourPackage.created_at.desc()).all()
    return jsonify([pkg.to_dict() for pkg in packages]), 200


@tour_bp.route('/admin/companies/<int:company_id>/packages', methods=['POST'])
@token_required
def create_package_admin(current_user, company_id):
    """Create a new package for a company (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json()
        
        package = TourPackage(
            company_id=company_id,
            name=data['name'],
            description=data['description'],
            short_description=data.get('short_description'),
            package_type=data['package_type'],
            pricing_model=data['pricing_model'],
            base_price=data['base_price'],
            currency=data.get('currency', 'KES'),
            price_per_kilometer=data.get('price_per_kilometer'),
            price_per_day=data.get('price_per_day'),
            price_per_night=data.get('price_per_night'),
            price_per_person=data.get('price_per_person'),
            price_per_vehicle=data.get('price_per_vehicle'),
            fixed_price=data.get('fixed_price'),
            duration_days=data.get('duration_days'),
            duration_nights=data.get('duration_nights'),
            estimated_distance_km=data.get('estimated_distance_km'),
            min_people=data.get('min_people', 1),
            max_people=data.get('max_people', 50),
            inclusions=','.join(data.get('inclusions', [])) if isinstance(data.get('inclusions'), list) else data.get('inclusions'),
            exclusions=','.join(data.get('exclusions', [])) if isinstance(data.get('exclusions'), list) else data.get('exclusions'),
            itinerary=data.get('itinerary'),
            is_available=data.get('is_available', True),
            available_from=datetime.strptime(data['available_from'], '%Y-%m-%d').date() if data.get('available_from') else None,
            available_to=datetime.strptime(data['available_to'], '%Y-%m-%d').date() if data.get('available_to') else None,
            default_discount_id=data.get('default_discount_id'),
            is_featured=data.get('is_featured', False)
        )
        
        db.session.add(package)
        db.session.commit()
        
        return jsonify(package.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/packages/<int:package_id>', methods=['PUT'])
@token_required
def update_package_admin(current_user, package_id):
    """Update a package (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        package = TourPackage.query.get_or_404(package_id)
        data = request.get_json()
        
        update_fields = ['name', 'description', 'short_description', 'package_type', 'pricing_model',
                        'base_price', 'currency', 'price_per_kilometer', 'price_per_day', 'price_per_night',
                        'price_per_person', 'price_per_vehicle', 'fixed_price', 'duration_days',
                        'duration_nights', 'estimated_distance_km', 'min_people', 'max_people',
                        'itinerary', 'is_available', 'default_discount_id', 'is_featured']
        
        for field in update_fields:
            if field in data:
                setattr(package, field, data[field])
        
        if 'inclusions' in data:
            package.inclusions = ','.join(data['inclusions']) if isinstance(data['inclusions'], list) else data['inclusions']
        if 'exclusions' in data:
            package.exclusions = ','.join(data['exclusions']) if isinstance(data['exclusions'], list) else data['exclusions']
        if 'available_from' in data and data['available_from']:
            package.available_from = datetime.strptime(data['available_from'], '%Y-%m-%d').date()
        if 'available_to' in data and data['available_to']:
            package.available_to = datetime.strptime(data['available_to'], '%Y-%m-%d').date()
        
        db.session.commit()
        return jsonify(package.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/packages/<int:package_id>', methods=['DELETE'])
@token_required
def delete_package_admin(current_user, package_id):
    """Delete a package (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    package = TourPackage.query.get_or_404(package_id)
    db.session.delete(package)
    db.session.commit()
    
    return jsonify({'message': 'Package deleted successfully'}), 200


@tour_bp.route('/admin/companies/<int:company_id>/discounts', methods=['GET'])
@token_required
def get_company_discounts_admin(current_user, company_id):
    """Get all discounts for a company (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    discounts = CompanyDiscount.query.filter_by(company_id=company_id).order_by(CompanyDiscount.created_at.desc()).all()
    return jsonify([d.to_dict() for d in discounts]), 200


@tour_bp.route('/admin/companies/<int:company_id>/discounts', methods=['POST'])
@token_required
def create_discount_admin(current_user, company_id):
    """Create a new discount for a company (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json()
        
        discount = CompanyDiscount(
            company_id=company_id,
            name=data['name'],
            description=data.get('description'),
            discount_code=data['discount_code'].upper(),
            discount_type=data['discount_type'],
            percentage_off=data.get('percentage_off'),
            fixed_amount_off=data.get('fixed_amount_off'),
            currency=data.get('currency', 'KES'),
            min_booking_value=data.get('min_booking_value'),
            min_number_of_people=data.get('min_number_of_people'),
            min_days_advance=data.get('min_days_advance'),
            max_days_advance=data.get('max_days_advance'),
            max_discount_amount=data.get('max_discount_amount'),
            max_discount_percentage=data.get('max_discount_percentage'),
            applies_to=data.get('applies_to', 'all'),
            specific_package_id=data.get('specific_package_id'),
            valid_from=datetime.strptime(data['valid_from'], '%Y-%m-%d').date(),
            valid_to=datetime.strptime(data['valid_to'], '%Y-%m-%d').date(),
            usage_limit=data.get('usage_limit'),
            per_user_limit=data.get('per_user_limit', 1),
            can_stack=data.get('can_stack', False),
            stack_priority=data.get('stack_priority', 0),
            is_active=data.get('is_active', True),
            is_public=data.get('is_public', True)
        )
        
        db.session.add(discount)
        db.session.commit()
        
        return jsonify(discount.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/discounts/<int:discount_id>', methods=['PUT'])
@token_required
def update_discount_admin(current_user, discount_id):
    """Update a discount (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        discount = CompanyDiscount.query.get_or_404(discount_id)
        data = request.get_json()
        
        update_fields = ['name', 'description', 'discount_code', 'discount_type', 'percentage_off',
                        'fixed_amount_off', 'currency', 'min_booking_value', 'min_number_of_people',
                        'min_days_advance', 'max_days_advance', 'max_discount_amount', 'max_discount_percentage',
                        'applies_to', 'specific_package_id', 'usage_limit', 'per_user_limit',
                        'can_stack', 'stack_priority', 'is_active', 'is_public']
        
        for field in update_fields:
            if field in data:
                if field == 'discount_code':
                    setattr(discount, field, data[field].upper())
                else:
                    setattr(discount, field, data[field])
        
        if 'valid_from' in data:
            discount.valid_from = datetime.strptime(data['valid_from'], '%Y-%m-%d').date()
        if 'valid_to' in data:
            discount.valid_to = datetime.strptime(data['valid_to'], '%Y-%m-%d').date()
        
        db.session.commit()
        return jsonify(discount.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/discounts/<int:discount_id>', methods=['DELETE'])
@token_required
def delete_discount_admin(current_user, discount_id):
    """Delete a discount (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    discount = CompanyDiscount.query.get_or_404(discount_id)
    db.session.delete(discount)
    db.session.commit()
    
    return jsonify({'message': 'Discount deleted successfully'}), 200


@tour_bp.route('/admin/companies/<int:company_id>/gallery', methods=['POST'])
@token_required
def add_gallery_image_admin(current_user, company_id):
    """Add a gallery image to company portfolio (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        company = TourCompany.query.get_or_404(company_id)
        
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        filename = secure_filename(f"company_{company_id}_gallery_{file.filename}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        thumbnail_filename = f"thumb_{filename}"
        
        gallery = TourCompanyGallery(
            company_id=company_id,
            image_url=filename,
            thumbnail_url=thumbnail_filename,
            caption=request.form.get('caption'),
            description=request.form.get('description'),
            location_name=request.form.get('location_name'),
            location_latitude=request.form.get('location_latitude', type=float),
            location_longitude=request.form.get('location_longitude', type=float),
            destination_id=request.form.get('destination_id', type=int),
            taken_date=datetime.strptime(request.form['taken_date'], '%Y-%m-%d').date() if request.form.get('taken_date') else None,
            photographer=request.form.get('photographer'),
            tags=request.form.get('tags'),
            is_featured=request.form.get('is_featured', 'false').lower() == 'true',
            display_order=request.form.get('display_order', 0, type=int)
        )
        
        db.session.add(gallery)
        db.session.commit()
        
        return jsonify(gallery.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/gallery/<int:gallery_id>', methods=['PUT'])
@token_required
def update_gallery_image_admin(current_user, gallery_id):
    """Update gallery image details (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        gallery = TourCompanyGallery.query.get_or_404(gallery_id)
        data = request.get_json()
        
        update_fields = ['caption', 'description', 'location_name', 'location_latitude', 
                        'location_longitude', 'destination_id', 'photographer', 'tags',
                        'is_featured', 'display_order']
        
        for field in update_fields:
            if field in data:
                setattr(gallery, field, data[field])
        
        if 'taken_date' in data and data['taken_date']:
            gallery.taken_date = datetime.strptime(data['taken_date'], '%Y-%m-%d').date()
        
        db.session.commit()
        return jsonify(gallery.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/gallery/<int:gallery_id>', methods=['DELETE'])
@token_required
def delete_gallery_image_admin(current_user, gallery_id):
    """Delete gallery image (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        gallery = TourCompanyGallery.query.get_or_404(gallery_id)
        
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], gallery.image_url)
        if os.path.exists(filepath):
            os.remove(filepath)
        
        db.session.delete(gallery)
        db.session.commit()
        
        return jsonify({'message': 'Gallery image deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


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
        
        filename = secure_filename(f"company_{company_id}_logo_{file.filename}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
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
        
        filename = secure_filename(f"company_{company_id}_img_{file.filename}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        caption = request.form.get('caption', '')
        is_primary = request.form.get('is_primary', 'false').lower() == 'true'
        
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
        
        TourCompanyImage.query.filter_by(company_id=image.company_id, is_primary=True).update({'is_primary': False})
        
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
        company = TourCompany.query.get_or_404(company_id)
        
        if not company.is_visible_to_users():
            return jsonify({'error': 'Images not available'}), 404
        
        images = TourCompanyImage.query.filter_by(company_id=company_id).all()
        return jsonify([img.to_dict() for img in images]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tour_bp.route('/admin/packages/<int:package_id>/upload-cover', methods=['POST'])
@token_required
def upload_package_cover(current_user, package_id):
    """Upload package cover image (admin only)"""
    if current_user.user_type != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        package = TourPackage.query.get_or_404(package_id)
        
        if 'cover' not in request.files:
            return jsonify({'error': 'No cover file provided'}), 400
        
        file = request.files['cover']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        filename = secure_filename(f"package_{package_id}_cover_{file.filename}")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        package.cover_image = filename
        db.session.commit()
        
        return jsonify({
            'message': 'Package cover image uploaded successfully',
            'cover_url': f"/api/uploads/{filename}"
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500