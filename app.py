import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
CORS(app, origins=['*'])

# Configure Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ElevenLabs config (for client integration)
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
ELEVENLABS_AGENT_ID = os.environ.get('ELEVENLABS_AGENT_ID', 'agent_4201ka0zmyzdexs9hhw24mce6rzb')

@app.route('/')
def index():
    return jsonify({
        'service': 'Aura AI - ElevenLabs + Gemini Backend',
        'status': 'running',
        'version': '1.0',
        'endpoints': {
            '/': 'API info',
            '/health': 'Health check',
            '/api/analyze': 'POST - Analyze conversation'
        }
    }), 200

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    Analyze conversation from ElevenLabs

    Request:
    {
        "id": "user123",
        "history": [
            {"role": "user", "content": "I keep procrastinating"},
            {"role": "assistant", "content": "Tell me more..."}
        ]
    }

    Response:
    {
        "analysis": "...",
        "user_id": "user123"
    }
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('id', 'anonymous')
        history = data.get('history', [])

        if not history:
            return jsonify({'error': 'History required'}), 400

        # Build conversation text
        conversation = "\n".join([
            f"{h.get('role', 'user')}: {h.get('content', '')}"
            for h in history
        ])

        # Gemini analyzes
        if GEMINI_API_KEY:
            model = genai.GenerativeModel('gemini-1.5-flash')

            prompt = f"""Analyze this CBT therapy conversation:

{conversation}

Provide:
1. Cognitive distortions identified
2. Progress assessment
3. Recommendations
4. Crisis risk (low/medium/high)

Format as JSON."""

            response = model.generate_content(prompt)

            return jsonify({
                'user_id': user_id,
                'analysis': response.text,
                'status': 'success'
            }), 200
        else:
            return jsonify({'error': 'Gemini not configured'}), 500

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
