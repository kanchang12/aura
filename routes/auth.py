from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Subscription, UsageStats
from datetime import datetime, timedelta
import re

auth_bp = Blueprint('auth', __name__)

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()

        # Validate required fields
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        nickname = data.get('nickname', '').strip()

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        if not is_valid_email(email):
            return jsonify({'error': 'Invalid email format'}), 400

        if len(password) < 8:
            return jsonify({'error': 'Password must be at least 8 characters'}), 400

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 409

        # Create user
        user = User(
            email=email,
            nickname=nickname or email.split('@')[0],
            data_consent=data.get('data_consent', False),
            marketing_consent=data.get('marketing_consent', False)
        )
        user.set_password(password)

        db.session.add(user)
        db.session.flush()

        # Create subscription (free tier)
        subscription = Subscription(
            user_id=user.id,
            is_premium=False,
            free_minutes_used=0,
            free_minutes_reset_at=datetime.utcnow() + timedelta(days=30)
        )
        db.session.add(subscription)

        # Create usage stats
        stats = UsageStats(user_id=user.id)
        db.session.add(stats)

        db.session.commit()

        # Log the user in
        login_user(user)

        return jsonify({
            'message': 'Registration successful',
            'user': user.to_dict(),
            'subscription': subscription.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid email or password'}), 401

        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 403

        login_user(user, remember=True)

        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'subscription': user.subscription.to_dict() if user.subscription else None
        }), 200

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout user"""
    logout_user()
    return jsonify({'message': 'Logout successful'}), 200

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current user info"""
    return jsonify({
        'user': current_user.to_dict(),
        'subscription': current_user.subscription.to_dict() if current_user.subscription else None,
        'usage_stats': current_user.usage_stats.to_dict() if current_user.usage_stats else None
    }), 200

@auth_bp.route('/delete-account', methods=['DELETE'])
@login_required
def delete_account():
    """Delete user account (GDPR compliance)"""
    try:
        user_id = current_user.id
        logout_user()

        user = User.query.get(user_id)
        db.session.delete(user)
        db.session.commit()

        return jsonify({'message': 'Account deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Account deletion error: {e}")
        return jsonify({'error': 'Failed to delete account'}), 500
