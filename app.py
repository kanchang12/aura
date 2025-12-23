from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from config import config
from models import db, User
import os

def create_app(config_name='development'):
    """Application factory pattern"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    CORS(app, origins=app.config['ALLOWED_ORIGINS'], supports_credentials=True)

    # Login manager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from routes.auth import auth_bp
    from routes.chat import chat_bp
    from routes.subscription import subscription_bp
    from routes.admin import admin_bp
    from routes.blog import blog_bp
    from routes.user import user_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(subscription_bp, url_prefix='/api/subscription')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(blog_bp, url_prefix='/api/blog')
    app.register_blueprint(user_bp, url_prefix='/api/user')

    # Create tables
    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    env = os.getenv('FLASK_ENV', 'development')
    app = create_app(env)
    app.run(host='0.0.0.0', port=5000, debug=(env == 'development'))
app = create_app('production')
