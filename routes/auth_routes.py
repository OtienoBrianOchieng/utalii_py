# routes/auth_routes.py
from flask import Blueprint, request, jsonify, current_app
from models.user import User
from utils.auth import token_required
from app import db
import re
import requests
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

# Disposable email domains (partial list)
DISPOSABLE_DOMAINS = {
    'tempmail.com', '10minutemail.com', 'guerrillamail.com', 'mailinator.com',
    'throwawaymail.com', 'yopmail.com', 'getairmail.com', 'tempmailaddress.com',
    'fakeinbox.com', 'trashmail.com', 'dispostable.com', 'maildrop.cc',
    'temp-mail.org', 'tempail.com', 'emailondeck.com', 'tmpmail.org'
}

def validate_email(email):
    """Validate email format and check disposable"""
    email = email.strip().lower()
    
    # Basic format check
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    # Check disposable
    domain = email.split('@')[1]
    if domain in DISPOSABLE_DOMAINS:
        return False, "Please use a permanent email address"
    
    return True, "Valid email"

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register new user"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['full_name', 'email', 'password', 'agreed_to_policy']
        for field in required:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate email
        is_valid, message = validate_email(data['email'])
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Check if user exists
        if User.query.filter_by(email=data['email'].lower()).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        # Validate password strength
        password = data['password']
        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400
        
        # Create user
        user = User(
            full_name=data['full_name'],
            email=data['email'].lower(),
            phone_number=data.get('phone_number'),
            user_type='visitor',
            agreed_to_policy=data['agreed_to_policy']
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Generate token
        token = user.generate_token()
        
        return jsonify({
            'message': 'Registration successful',
            'token': token,
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        # Find user
        user = User.query.filter_by(email=data['email'].lower()).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        # Generate token
        token = user.generate_token()
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    """Get current user profile"""
    return jsonify(current_user.to_dict()), 200

@auth_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile(current_user):
    """Update user profile"""
    try:
        data = request.get_json()
        
        # Update allowed fields
        if 'full_name' in data:
            current_user.full_name = data['full_name']
        if 'phone_number' in data:
            current_user.phone_number = data['phone_number']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated',
            'user': current_user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """Verify if token is valid"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({'valid': False}), 400
        
        user = User.verify_token(token)
        
        if user:
            return jsonify({
                'valid': True,
                'user': user.to_dict()
            }), 200
        else:
            return jsonify({'valid': False}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500