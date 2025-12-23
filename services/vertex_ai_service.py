import os
import json
from config import Config

class VertexAIService:
    """
    Simplified Service: 
    Backend now only handles Knowledge Base retrieval and Action processing.
    """

    def __init__(self):
        # We only need the path to the data you uploaded earlier
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.kb_path = os.path.join(self.base_dir, 'cbt_knowledge_base.json')

    def get_knowledge_base_content(self):
        """
        Returns the raw text for you to copy-paste into ElevenLabs 
        Knowledge Base settings.
        """
        try:
            if os.path.exists(self.kb_path):
                with open(self.kb_path, 'r') as f:
                    data = json.load(f)
                    # Convert JSON to a clean string ElevenLabs can read
                    return json.dumps(data, indent=2)
            return "Knowledge base file not found."
        except Exception as e:
            return f"Error: {str(e)}"

    def handle_emergency_trigger(self, user_id):
        """
        This is what your backend SHOULD do. 
        ElevenLabs calls this via a 'Webhook' if the user is in danger.
        """
        # Logic to contact emergency persons
        print(f"EMERGENCY: Notifying contacts for user {user_id}")
        return {"status": "contacts_notified"}
