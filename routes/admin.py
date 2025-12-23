from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, User, Subscription, Session, UsageStats, BlogPost
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_dashboard():
    """Get admin dashboard statistics"""
    try:
        # Total users
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()

        # Premium subscriptions
        premium_users = Subscription.query.filter_by(is_premium=True).count()

        # Sessions statistics
        total_sessions = Session.query.count()
        today_sessions = Session.query.filter(
            Session.started_at >= datetime.utcnow().date()
        ).count()

        # Revenue (estimate based on premium users)
        monthly_revenue = premium_users * 9.99

        # Recent registrations (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_registrations = User.query.filter(
            User.created_at >= week_ago
        ).count()

        # Average session duration
        avg_duration = db.session.query(
            func.avg(Session.duration_minutes)
        ).scalar() or 0

        return jsonify({
            'total_users': total_users,
            'active_users': active_users,
            'premium_users': premium_users,
            'total_sessions': total_sessions,
            'today_sessions': today_sessions,
            'monthly_revenue': f'${monthly_revenue:.2f}',
            'recent_registrations': recent_registrations,
            'avg_session_duration': round(avg_duration, 2)
        }), 200

    except Exception as e:
        print(f"Error fetching dashboard: {e}")
        return jsonify({'error': 'Failed to fetch dashboard'}), 500

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users():
    """Get paginated list of users"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '')

        query = User.query

        if search:
            query = query.filter(
                (User.email.ilike(f'%{search}%')) |
                (User.nickname.ilike(f'%{search}%'))
            )

        users = query.order_by(User.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'users': [
                {
                    **user.to_dict(),
                    'subscription': user.subscription.to_dict() if user.subscription else None,
                    'usage_stats': user.usage_stats.to_dict() if user.usage_stats else None
                }
                for user in users.items
            ],
            'total': users.total,
            'pages': users.pages,
            'current_page': page
        }), 200

    except Exception as e:
        print(f"Error fetching users: {e}")
        return jsonify({'error': 'Failed to fetch users'}), 500

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user_detail(user_id):
    """Get detailed information about a specific user"""
    try:
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Get user's sessions
        sessions = Session.query.filter_by(user_id=user_id)\
            .order_by(Session.started_at.desc())\
            .limit(20)\
            .all()

        return jsonify({
            'user': user.to_dict(),
            'subscription': user.subscription.to_dict() if user.subscription else None,
            'usage_stats': user.usage_stats.to_dict() if user.usage_stats else None,
            'recent_sessions': [session.to_dict() for session in sessions]
        }), 200

    except Exception as e:
        print(f"Error fetching user detail: {e}")
        return jsonify({'error': 'Failed to fetch user detail'}), 500

@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    """Activate or deactivate a user"""
    try:
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.is_active = not user.is_active
        db.session.commit()

        return jsonify({
            'message': f'User {"activated" if user.is_active else "deactivated"} successfully',
            'is_active': user.is_active
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error toggling user active status: {e}")
        return jsonify({'error': 'Failed to update user'}), 500

@admin_bp.route('/sessions', methods=['GET'])
@admin_required
def get_all_sessions():
    """Get paginated list of all sessions"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        sessions = Session.query.order_by(Session.started_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'sessions': [
                {
                    **session.to_dict(),
                    'user_email': session.user.email
                }
                for session in sessions.items
            ],
            'total': sessions.total,
            'pages': sessions.pages,
            'current_page': page
        }), 200

    except Exception as e:
        print(f"Error fetching sessions: {e}")
        return jsonify({'error': 'Failed to fetch sessions'}), 500

@admin_bp.route('/analytics', methods=['GET'])
@admin_required
def get_analytics():
    """Get detailed analytics"""
    try:
        # User growth over last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        user_growth = db.session.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('count')
        ).filter(
            User.created_at >= thirty_days_ago
        ).group_by(
            func.date(User.created_at)
        ).all()

        # Session activity over last 30 days
        session_activity = db.session.query(
            func.date(Session.started_at).label('date'),
            func.count(Session.id).label('count'),
            func.sum(Session.duration_minutes).label('total_minutes')
        ).filter(
            Session.started_at >= thirty_days_ago
        ).group_by(
            func.date(Session.started_at)
        ).all()

        # Most common cognitive distortions
        # This would require more complex query - simplified for now
        common_distortions = {}

        return jsonify({
            'user_growth': [
                {'date': row.date.isoformat(), 'count': row.count}
                for row in user_growth
            ],
            'session_activity': [
                {
                    'date': row.date.isoformat(),
                    'sessions': row.count,
                    'total_minutes': row.total_minutes or 0
                }
                for row in session_activity
            ],
            'common_distortions': common_distortions
        }), 200

    except Exception as e:
        print(f"Error fetching analytics: {e}")
        return jsonify({'error': 'Failed to fetch analytics'}), 500
