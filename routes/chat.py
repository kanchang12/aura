from flask import Blueprint, request, jsonify
from services.vertex_ai_service import VertexAIService

chat_bp = Blueprint('chat', __name__)
# Initialize inside the route file but outside the request for speed
vertex_service = VertexAIService()

@chat_bp.route('', methods=['POST'])
@chat_bp.route('/', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    
    # Vertex handles the logic, but remember ElevenLabs is the primary voice
    response = vertex_service.analyze_message(user_message)
    return jsonify(response)
