# routes/destination_routes.py
from flask import Blueprint, request, jsonify, send_from_directory, current_app
# from models.destination import Destination, Review, DestinationImage
# from models.user import User
from utils.auth import token_required, optional_token
from models import db, User, Destination, Review, DestinationImage  
from sqlalchemy import func
import os

destination_bp = Blueprint('destinations', __name__)

# Serve uploaded images
@destination_bp.route('/uploads/<path:filename>', methods=['GET'])
def get_upload(filename):
    """Serve uploaded files"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@destination_bp.route('/', methods=['GET'])
def get_destinations():
    """Get all destinations (public)"""
    try:
        category = request.args.get('category')
        region = request.args.get('region')
        search = request.args.get('search')
        
        query = Destination.query
        
        if category:
            query = query.filter_by(category=category)
        if region:
            query = query.filter_by(region=region)
        if search:
            query = query.filter(Destination.name.ilike(f'%{search}%'))
        
        destinations = query.all()
        result = []
        
        for dest in destinations:
            dest_dict = dest.to_dict()
            # Calculate average rating
            avg_rating = db.session.query(func.avg(Review.rating)).filter_by(destination_id=dest.id).scalar()
            dest_dict['average_rating'] = round(avg_rating, 1) if avg_rating else None
            result.append(dest_dict)
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@destination_bp.route('/<int:dest_id>', methods=['GET'])
def get_destination(dest_id):
    """Get single destination with details (public)"""
    try:
        destination = Destination.query.get_or_404(dest_id)
        
        result = destination.to_dict_detail()
        
        # Calculate average rating
        avg_rating = db.session.query(func.avg(Review.rating)).filter_by(destination_id=dest_id).scalar()
        result['average_rating'] = round(avg_rating, 1) if avg_rating else None
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@destination_bp.route('/<int:dest_id>/reviews', methods=['POST'])
@token_required
def add_review(current_user, dest_id):
    """Add review to destination (authenticated users only)"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('rating') or not data.get('comment'):
            return jsonify({'error': 'Rating and comment required'}), 400
        
        # Check if user already reviewed this destination
        existing = Review.query.filter_by(
            destination_id=dest_id, 
            user_id=current_user.id
        ).first()
        
        if existing:
            return jsonify({'error': 'You have already reviewed this destination'}), 400
        
        # Create review
        review = Review(
            destination_id=dest_id,
            user_id=current_user.id,
            rating=data['rating'],
            comment=data['comment'],
            visit_date=data.get('visit_date')
        )
        
        db.session.add(review)
        db.session.commit()
        
        return jsonify(review.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@destination_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all destination categories (public)"""
    try:
        categories = db.session.query(Destination.category).distinct().all()
        return jsonify([c[0] for c in categories if c[0]]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@destination_bp.route('/regions', methods=['GET'])
def get_regions():
    """Get all regions (public)"""
    try:
        regions = db.session.query(Destination.region).distinct().all()
        return jsonify([r[0] for r in regions if r[0]]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500