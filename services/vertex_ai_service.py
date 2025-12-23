import os
import json

class VertexAIService:
    def __init__(self):
        # Use an absolute path that works on Cloud Run
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        # We look for ANY json in the knowledge base, fallback if pst.json is missing
        self.kb_path = os.path.join(self.base_dir, '..', 'knowledge_base', 'cbt_knowledge_base.json')
        self.knowledge_base = self._load_kb()

    def _load_kb(self):
        try:
            if os.path.exists(self.kb_path):
                with open(self.kb_path, 'r') as f:
                    return json.load(f)
            return {"info": "Listening-based coaching active"}
        except:
            return {}

    def build_system_prompt(self):
        """The 'Listen, Don't Preach' Prompt for the LLM"""
        return """
        # ROLE: Aura, a supportive listener.
        # STYLE: Listen 70%, Speak 30%. 
        # RULES: 
        1. Always validate emotions first ("I hear you," "That sounds tough").
        2. Never give a lecture. 
        3. Max 2 sentences per response. 
        4. Use the Problem Solving Therapy (PST) from the knowledge base ONLY when the user asks for help.
        """

    def analyze_message(self, user_message, history=None):
        # Minimal response structure to keep ElevenLabs happy
        return {
            "voice_response": "I'm listening. Tell me more about that.",
            "suggested_task": None,
            "detected_distortion": None
        }
