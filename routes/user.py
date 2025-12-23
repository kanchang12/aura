from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from models import db, Session, Message
import json
from io import BytesIO
from datetime import datetime

user_bp = Blueprint('user', __name__)

@user_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Get user profile"""
    return jsonify({
        'user': current_user.to_dict(),
        'subscription': current_user.subscription.to_dict() if current_user.subscription else None,
        'usage_stats': current_user.usage_stats.to_dict() if current_user.usage_stats else None
    }), 200

@user_bp.route('/profile', methods=['PUT'])
@login_required
def update_profile():
    """Update user profile"""
    try:
        data = request.get_json()

        if 'nickname' in data:
            current_user.nickname = data['nickname'].strip()

        if 'marketing_consent' in data:
            current_user.marketing_consent = data['marketing_consent']

        db.session.commit()

        return jsonify({
            'message': 'Profile updated successfully',
            'user': current_user.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error updating profile: {e}")
        return jsonify({'error': 'Failed to update profile'}), 500

@user_bp.route('/export-data', methods=['GET'])
@login_required
def export_data():
    """Export all user data (GDPR compliance)"""
    try:
        # Compile all user data
        user_data = {
            'user': current_user.to_dict(),
            'subscription': current_user.subscription.to_dict() if current_user.subscription else None,
            'usage_stats': current_user.usage_stats.to_dict() if current_user.usage_stats else None,
            'sessions': []
        }

        # Get all sessions
        sessions = Session.query.filter_by(user_id=current_user.id).all()

        for session in sessions:
            session_data = session.to_dict(include_transcript=True)

            # Get messages
            messages = Message.query.filter_by(session_id=session.id).all()
            session_data['messages'] = [
                {
                    'role': msg.role,
                    'content': msg.content,
                    'timestamp': msg.timestamp.isoformat()
                }
                for msg in messages
            ]

            user_data['sessions'].append(session_data)

        # Convert to JSON
        json_data = json.dumps(user_data, indent=2)

        # Create file
        buffer = BytesIO(json_data.encode())
        buffer.seek(0)

        return send_file(
            buffer,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'aura_data_{current_user.id}_{datetime.utcnow().strftime("%Y%m%d")}.json'
        )

    except Exception as e:
        print(f"Error exporting data: {e}")
        return jsonify({'error': 'Failed to export data'}), 500

@user_bp.route('/journey', methods=['GET'])
@login_required
def get_journey():
    """Get user journey statistics for profile screen"""
    try:
        stats = current_user.usage_stats

        if not stats:
            return jsonify({'error': 'No usage stats found'}), 404

        # Get recent sessions for journey insights
        recent_sessions = Session.query.filter_by(user_id=current_user.id)\
            .order_by(Session.started_at.desc())\
            .limit(10)\
            .all()

        # Collect insights
        insights = []

        # Total time spent
        if stats.total_minutes > 0:
            insights.append({
                'title': 'Total Time Invested',
                'description': f"You've spent {stats.total_minutes} minutes working on yourself."
            })

        # Tasks created
        if stats.total_tasks_created > 0:
            completion_rate = (stats.total_tasks_completed / stats.total_tasks_created) * 100 if stats.total_tasks_created > 0 else 0
            insights.append({
                'title': 'Tasks Created',
                'description': f"You've created {stats.total_tasks_created} tasks with a {completion_rate:.0f}% completion rate."
            })

        # Streak
        if stats.streak_days > 0:
            insights.append({
                'title': 'Current Streak',
                'description': f"You're on a {stats.streak_days}-day streak. Keep it up!"
            })

        return jsonify({
            'usage_stats': stats.to_dict(),
            'insights': insights,
            'recent_sessions': [
                {
                    'date': session.started_at.strftime('%B %d, %Y'),
                    'duration': session.duration_minutes,
                    'tasks_created': len(session.tasks_created) if session.tasks_created else 0
                }
                for session in recent_sessions
            ]
        }), 200

    except Exception as e:
        print(f"Error fetching journey: {e}")
        return jsonify({'error': 'Failed to fetch journey'}), 500
