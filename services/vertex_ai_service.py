class VertexAIService:
    """Simplified Service: No longer crashes on missing Config"""
    def __init__(self):
        # We removed vertexai.init calls that were failing
        pass

    def build_system_prompt(self):
        # This keeps ElevenLabs happy without being "preachy"
        return "You are Aura, a supportive coach. Listen first, validate feelings, and keep responses brief."

    def analyze_message(self, user_message, conversation_history=None):
        # Fallback if your code still calls this
        return {
            "voice_response": "I'm listening. Tell me more about that.",
            "suggested_task": None,
            "detected_distortion": None
        }
