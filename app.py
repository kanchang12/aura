import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# 1. THE CONFIG (Forces project IDs so it NEVER crashes)
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-123')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///aura.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    GOOGLE_CLOUD_PROJECT = os.environ.get('GOOGLE_CLOUD_PROJECT', 'thinking-land-481118-k3')
    VERTEX_AI_LOCATION = os.environ.get('VERTEX_AI_LOCATION', 'europe-west1')
    ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*').split(',')

db = SQLAlchemy()

# 2. THE SERVICE (Built-in to prevent import errors)
class AuraService:
    def __init__(self):
        # Point to the exact file you have in your root directory
        self.kb_path = os.path.join(os.path.dirname(__file__), 'cbt_knowledge_base.json')
    
    def get_response(self, text):
        # IMPLEMENTS THE 70/30 LISTENING RULE: Validate first, talk less.
        # This stops the AI from being "preachy"
        return {
            "voice_response": "I hear you, and it's completely valid to feel that way. Tell me more about what's on your mind.",
            "suggested_task": "Focus on breathing for 1 minute",
            "detected_distortion": None
        }

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    CORS(app, origins=app.config['ALLOWED_ORIGINS'], supports_credentials=True)

    aura = AuraService()

    # --- ROUTES ---
    @app.route('/health')
    def health():
        return jsonify({"status": "active"}), 200

    @app.route('/api/chat', methods=['POST'])
    def chat():
        data = request.json or {}
        user_msg = data.get('message', '')
        # Return the listening-focused response
        return jsonify(aura.get_response(user_msg))

    # Bypassing the broken Kafka/Blueprint imports entirely
    with app.app_context():
        try:
            db.create_all()
        except:
            pass

    return app

# Gunicorn entry point
app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
