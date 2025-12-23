from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Session, Message, UsageStats
from services.vertex_ai_service import VertexAIService
from services.elevenlabs_service import ElevenLabsService
from services.confluent_service import ConfluentService
from datetime import datetime
import os
from cryptography.fernet import Fernet

chat_bp = Blueprint('chat', __name__)

# Initialize services
vertex_ai = VertexAIService()
elevenlabs = ElevenLabsService()
confluent = ConfluentService()

@chat_bp.route('/start-session', methods=['POST'])
@login_required
def start_session():
    """Start a new chat session"""
    try:
        # Check if user has available minutes
        if not current_user.subscription.has_available_minutes(0):
            return jsonify({
                'error': 'You have exceeded your free minutes for this month',
                'upgrade_required': True
            }), 403

        # Create new session
        session = Session(
            user_id=current_user.id,
            started_at=datetime.utcnow(),
            detected_distortions=[],
            tasks_created=[]
        )
        db.session.add(session)
        db.session.commit()

        # Publish session started event to Confluent
        confluent.publish_session_event(current_user.id, {
            'session_id': session.id,
            'started_at': session.started_at.isoformat(),
            'event_type': 'session_started'
        })

        # Start ElevenLabs conversation
        conversation_session = elevenlabs.start_conversation(current_user.id, session.id)

        return jsonify({
            'session_id': session.id,
            'conversation': conversation_session,
            'message': 'Session started successfully'
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Error starting session: {e}")
        return jsonify({'error': 'Failed to start session'}), 500

@chat_bp.route('/send-message', methods=['POST'])
@login_required
def send_message():
    """Send a message in the chat session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        user_message = data.get('message')

        if not session_id or not user_message:
            return jsonify({'error': 'Session ID and message are required'}), 400

        # Get session
        session = Session.query.get(session_id)
        if not session or session.user_id != current_user.id:
            return jsonify({'error': 'Session not found'}), 404

        if session.ended_at:
            return jsonify({'error': 'Session has ended'}), 400

        # Save user message
        user_msg = Message(
            session_id=session_id,
            role='user',
            content=user_message,
            timestamp=datetime.utcnow()
        )
        db.session.add(user_msg)

        # Get conversation history
        history = Message.query.filter_by(session_id=session_id).order_by(Message.timestamp).all()
        conversation_history = [
            {'role': msg.role, 'content': msg.content}
            for msg in history
        ]

        # Get AI response from Vertex AI
        ai_response = vertex_ai.analyze_message(user_message, conversation_history)

        # Save assistant message
        assistant_msg = Message(
            session_id=session_id,
            role='assistant',
            content=ai_response['voice_response'],
            timestamp=datetime.utcnow()
        )
        db.session.add(assistant_msg)

        # Update session with detected distortions and tasks
        if ai_response.get('detected_distortion'):
            if not session.detected_distortions:
                session.detected_distortions = []
            session.detected_distortions.append(ai_response['detected_distortion'])

        if ai_response.get('suggested_task'):
            if not session.tasks_created:
                session.tasks_created = []
            task_data = {
                'description': ai_response['suggested_task'],
                'created_at': datetime.utcnow().isoformat()
            }
            session.tasks_created.append(task_data)

            # Publish task event to Confluent
            confluent.publish_task_event(current_user.id, task_data)

        db.session.commit()

        # Convert to speech using ElevenLabs
        audio_data = elevenlabs.text_to_speech(ai_response['voice_response'])

        return jsonify({
            'voice_response': ai_response['voice_response'],
            'suggested_task': ai_response.get('suggested_task'),
            'detected_distortion': ai_response.get('detected_distortion'),
            'audio_available': audio_data is not None
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error sending message: {e}")
        return jsonify({'error': 'Failed to send message'}), 500

@chat_bp.route('/end-session', methods=['POST'])
@login_required
def end_session():
    """End a chat session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({'error': 'Session ID is required'}), 400

        # Get session
        session = Session.query.get(session_id)
        if not session or session.user_id != current_user.id:
            return jsonify({'error': 'Session not found'}), 404

        if session.ended_at:
            return jsonify({'error': 'Session already ended'}), 400

        # Calculate duration
        session.ended_at = datetime.utcnow()
        duration = (session.ended_at - session.started_at).total_seconds() / 60
        session.duration_minutes = int(duration)

        # Generate session summary using Vertex AI
        messages = Message.query.filter_by(session_id=session_id).all()
        message_list = [
            {'role': msg.role, 'content': msg.content}
            for msg in messages
        ]
        summary = vertex_ai.generate_session_summary(message_list)

        # Encrypt summary
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if encryption_key:
            fernet = Fernet(encryption_key.encode())
            session.encrypted_summary = fernet.encrypt(summary.encode()).decode()

        # Update usage stats
        stats = current_user.usage_stats
        if stats:
            stats.total_sessions += 1
            stats.total_minutes += session.duration_minutes
            stats.monthly_sessions += 1
            stats.monthly_minutes += session.duration_minutes
            stats.last_session_at = session.ended_at
            stats.total_tasks_created += len(session.tasks_created) if session.tasks_created else 0

        # Consume minutes from subscription
        current_user.subscription.consume_minutes(session.duration_minutes)

        db.session.commit()

        # Publish session ended event to Confluent
        confluent.publish_session_event(current_user.id, {
            'session_id': session.id,
            'ended_at': session.ended_at.isoformat(),
            'duration_minutes': session.duration_minutes,
            'event_type': 'session_ended'
        })

        return jsonify({
            'message': 'Session ended successfully',
            'duration_minutes': session.duration_minutes,
            'summary': summary,
            'tasks_created': len(session.tasks_created) if session.tasks_created else 0
        }), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error ending session: {e}")
        return jsonify({'error': 'Failed to end session'}), 500

@chat_bp.route('/sessions', methods=['GET'])
@login_required
def get_sessions():
    """Get user's session history"""
    try:
        sessions = Session.query.filter_by(user_id=current_user.id)\
            .order_by(Session.started_at.desc())\
            .limit(50)\
            .all()

        return jsonify({
            'sessions': [session.to_dict() for session in sessions]
        }), 200

    except Exception as e:
        print(f"Error fetching sessions: {e}")
        return jsonify({'error': 'Failed to fetch sessions'}), 500

@chat_bp.route('/get-audio/<int:message_id>', methods=['GET'])
@login_required
def get_audio(message_id):
    """Get audio for a specific message"""
    try:
        message = Message.query.get(message_id)

        if not message:
            return jsonify({'error': 'Message not found'}), 404

        # Verify user owns this session
        session = Session.query.get(message.session_id)
        if not session or session.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        # Generate audio if not exists
        if message.role == 'assistant':
            audio_data = elevenlabs.text_to_speech(message.content)

            if audio_data:
                from flask import send_file
                from io import BytesIO

                return send_file(
                    BytesIO(audio_data),
                    mimetype='audio/mpeg',
                    as_attachment=True,
                    download_name=f'message_{message_id}.mp3'
                )

        return jsonify({'error': 'Audio not available'}), 404

    except Exception as e:
        print(f"Error getting audio: {e}")
        return jsonify({'error': 'Failed to get audio'}), 500
