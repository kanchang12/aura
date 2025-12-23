from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import os

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model with GDPR compliance"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)

    # Privacy settings
    data_consent = db.Column(db.Boolean, default=False)
    marketing_consent = db.Column(db.Boolean, default=False)

    # Relationships
    subscription = db.relationship('Subscription', backref='user', uselist=False, cascade='all, delete-orphan')
    sessions = db.relationship('Session', backref='user', cascade='all, delete-orphan')
    usage_stats = db.relationship('UsageStats', backref='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'nickname': self.nickname,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }

class Subscription(db.Model):
    """Subscription model for freemium tracking"""
    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Subscription type
    is_premium = db.Column(db.Boolean, default=False)
    stripe_customer_id = db.Column(db.String(255), unique=True)
    stripe_subscription_id = db.Column(db.String(255), unique=True)

    # Billing
    current_period_start = db.Column(db.DateTime)
    current_period_end = db.Column(db.DateTime)
    cancel_at_period_end = db.Column(db.Boolean, default=False)

    # Free tier tracking (reset monthly)
    free_minutes_used = db.Column(db.Integer, default=0)
    free_minutes_reset_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def has_available_minutes(self, duration_minutes):
        """Check if user can use the service"""
        if self.is_premium:
            return True

        # Reset monthly free minutes if needed
        if datetime.utcnow() > self.free_minutes_reset_at:
            self.free_minutes_used = 0
            self.free_minutes_reset_at = datetime.utcnow() + timedelta(days=30)
            db.session.commit()

        free_limit = int(os.getenv('FREE_MINUTES_PER_MONTH', 60))
        return (self.free_minutes_used + duration_minutes) <= free_limit

    def consume_minutes(self, duration_minutes):
        """Track usage for free tier"""
        if not self.is_premium:
            self.free_minutes_used += duration_minutes
            db.session.commit()

    def to_dict(self):
        return {
            'is_premium': self.is_premium,
            'free_minutes_used': self.free_minutes_used,
            'free_minutes_remaining': max(0, 60 - self.free_minutes_used),
            'free_minutes_reset_at': self.free_minutes_reset_at.isoformat() if self.free_minutes_reset_at else None,
            'current_period_end': self.current_period_end.isoformat() if self.current_period_end else None
        }

class Session(db.Model):
    """Chat session model with encryption for privacy"""
    __tablename__ = 'sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Session metadata
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    duration_minutes = db.Column(db.Integer, default=0)

    # Encrypted session data
    encrypted_summary = db.Column(db.Text)  # AI context summary (encrypted)
    encrypted_transcript = db.Column(db.Text)  # Full conversation (encrypted)

    # CBT tracking
    detected_distortions = db.Column(db.JSON)  # List of cognitive distortions identified
    tasks_created = db.Column(db.JSON)  # Micro-tasks suggested

    # Relationships
    messages = db.relationship('Message', backref='session', cascade='all, delete-orphan')

    def encrypt_data(self, data, encryption_key):
        """Encrypt sensitive data"""
        fernet = Fernet(encryption_key.encode())
        return fernet.encrypt(data.encode()).decode()

    def decrypt_data(self, encrypted_data, encryption_key):
        """Decrypt sensitive data"""
        fernet = Fernet(encryption_key.encode())
        return fernet.decrypt(encrypted_data.encode()).decode()

    def to_dict(self, include_transcript=False):
        result = {
            'id': self.id,
            'started_at': self.started_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'duration_minutes': self.duration_minutes,
            'detected_distortions': self.detected_distortions,
            'tasks_created': self.tasks_created
        }
        if include_transcript and self.encrypted_summary:
            # Only include if user requests (GDPR data export)
            result['summary'] = '[Encrypted - requires decryption]'
        return result

class Message(db.Model):
    """Individual message in a session"""
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)

    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Audio reference (if voice message)
    audio_url = db.Column(db.String(500))

class UsageStats(db.Model):
    """User journey tracking and analytics"""
    __tablename__ = 'usage_stats'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Overall stats
    total_sessions = db.Column(db.Integer, default=0)
    total_minutes = db.Column(db.Integer, default=0)
    total_tasks_created = db.Column(db.Integer, default=0)
    total_tasks_completed = db.Column(db.Integer, default=0)

    # This month stats
    monthly_sessions = db.Column(db.Integer, default=0)
    monthly_minutes = db.Column(db.Integer, default=0)
    monthly_reset_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=30))

    # Engagement
    last_session_at = db.Column(db.DateTime)
    streak_days = db.Column(db.Integer, default=0)

    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'total_sessions': self.total_sessions,
            'total_minutes': self.total_minutes,
            'monthly_sessions': self.monthly_sessions,
            'monthly_minutes': self.monthly_minutes,
            'tasks_created': self.total_tasks_created,
            'tasks_completed': self.total_tasks_completed,
            'streak_days': self.streak_days,
            'last_session_at': self.last_session_at.isoformat() if self.last_session_at else None
        }

class BlogPost(db.Model):
    """Blog posts for organic growth"""
    __tablename__ = 'blog_posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(250), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.Text)

    # SEO
    meta_description = db.Column(db.String(160))
    meta_keywords = db.Column(db.String(255))

    # Author and publishing
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    published = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'excerpt': self.excerpt,
            'content': self.content,
            'published': self.published,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at': self.created_at.isoformat()
        }
