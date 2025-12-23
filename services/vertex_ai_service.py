import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession
from google.cloud import aiplatform
import json
import os
from config import Config

class VertexAIService:
    """Google Vertex AI service for CBT conversation logic"""

    def __init__(self):
        # Initialize Vertex AI
        vertexai.init(
            project=Config.GOOGLE_CLOUD_PROJECT,
            location=Config.VERTEX_AI_LOCATION
        )
        self.model = GenerativeModel("gemini-1.5-pro")

        # Load CBT knowledge base
        self.knowledge_base = self._load_knowledge_base()

    def _load_knowledge_base(self):
        """Load JSON knowledge base files"""
        kb_path = os.path.join(os.path.dirname(__file__), '..', 'knowledge_base')
        knowledge = {}

        try:
            # Load PST framework
            with open(os.path.join(kb_path, 'pst.json'), 'r') as f:
                knowledge['pst'] = json.load(f)

            # Load Behavioral Activation
            with open(os.path.join(kb_path, 'behavioral_activation.json'), 'r') as f:
                knowledge['behavioral_activation'] = json.load(f)

            # Load Cognitive Distortions
            with open(os.path.join(kb_path, 'cognitive_distortions.json'), 'r') as f:
                knowledge['cognitive_distortions'] = json.load(f)

        except FileNotFoundError as e:
            print(f"Warning: Knowledge base file not found: {e}")
            knowledge = {}

        return knowledge

    def build_system_prompt(self):
        """Build the CBT coaching system prompt"""
        return f"""# ROLE
You are "Aura," an empathetic, high-energy CBT-based Anti-Procrastination Coach. Your goal is to help users break the cycle of task avoidance using evidence-based Cognitive Behavioral Therapy techniques.

# KNOWLEDGE BASE & CONTEXT
You must base your therapeutic logic on the provided JSON knowledge bases:
{json.dumps(self.knowledge_base, indent=2)}

1. Use the "Problem-Solving Therapy (PST)" framework to help users define tasks, generate alternatives, and make action plans.
2. Use "Behavioral Activation" principles to encourage "activity scheduling" and "checklist making" to counter low motivation.
3. Reference the "Cognitive Distortions" list, but specifically focus on procrastination triggers: "All-or-nothing thinking" (if I can't do it perfectly, why start?) and "Emotional Reasoning" (I don't feel like doing it, so I shouldn't).

# OPERATIONAL GUIDELINES (VOICE-FIRST / ELEVENLABS)
- You are communicating via VOICE (ElevenLabs). Keep responses concise (under 3 sentences).
- Use a warm, conversational, and encouraging tone. Avoid clinical jargon.
- Instead of "You are experiencing a cognitive distortion," say "It sounds like you're being a bit hard on yourself; let's try looking at this a different way."

# TASK INTERVENTION STRATEGY
When a user expresses dread or avoidance:
1. VALIDATE: Briefly acknowledge the feeling (e.g., "It's totally normal to feel overwhelmed by a big project").
2. MICRO-TASK: Apply the PST technique from the knowledge base—ask the user for the "smallest, silliest first step" that takes less than 2 minutes.
3. SCHEDULE: Use Confluent-style thinking—ask "When exactly in the next hour will you do this?"

# SAFETY & ETHICS (MANDATORY)
- If the user expresses severe distress or self-harm, immediately pivot to a safety protocol: "I'm concerned about what you're saying. Please reach out to a crisis helpline or a mental health professional immediately."
- Do not provide medical diagnoses.
- This is a coaching app, not a medical treatment.

# OUTPUT FORMAT
- Always output a clean JSON response containing:
{{
  "voice_response": "The text for ElevenLabs to speak",
  "suggested_task": "A short string for the Android UI (if applicable)",
  "detected_distortion": "The name of the CBT distortion identified (if any)"
}}
"""

    def analyze_message(self, user_message, conversation_history=None):
        """
        Analyze user message using Gemini and return CBT response

        Args:
            user_message: Current user message
            conversation_history: List of previous messages for context

        Returns:
            dict: JSON response with voice_response, suggested_task, detected_distortion
        """
        try:
            # Build conversation context
            chat = self.model.start_chat()

            # Add system prompt
            system_prompt = self.build_system_prompt()

            # Add conversation history if available
            full_prompt = system_prompt + "\n\n# CONVERSATION HISTORY\n"
            if conversation_history:
                for msg in conversation_history[-5:]:  # Last 5 messages for context
                    full_prompt += f"{msg['role']}: {msg['content']}\n"

            full_prompt += f"\n# CURRENT USER MESSAGE\n{user_message}\n\n"
            full_prompt += "Please respond with a JSON object following the OUTPUT FORMAT specified above."

            # Get response from Gemini
            response = chat.send_message(full_prompt)
            response_text = response.text

            # Try to parse JSON from response
            try:
                # Extract JSON from markdown code blocks if present
                if '```json' in response_text:
                    json_start = response_text.find('```json') + 7
                    json_end = response_text.find('```', json_start)
                    response_text = response_text[json_start:json_end].strip()
                elif '```' in response_text:
                    json_start = response_text.find('```') + 3
                    json_end = response_text.find('```', json_start)
                    response_text = response_text[json_start:json_end].strip()

                result = json.loads(response_text)

                # Validate required fields
                if 'voice_response' not in result:
                    result['voice_response'] = "I'm here to help you. What's on your mind today?"
                if 'suggested_task' not in result:
                    result['suggested_task'] = None
                if 'detected_distortion' not in result:
                    result['detected_distortion'] = None

                return result

            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "voice_response": response_text[:500],  # Limit length
                    "suggested_task": None,
                    "detected_distortion": None
                }

        except Exception as e:
            print(f"Error in Vertex AI service: {e}")
            return {
                "voice_response": "I'm having a bit of trouble right now. Can you try saying that again?",
                "suggested_task": None,
                "detected_distortion": None
            }

    def generate_session_summary(self, messages):
        """
        Generate a summary of the session for AI context continuity

        Args:
            messages: List of messages from the session

        Returns:
            str: Summary text
        """
        try:
            prompt = f"""Based on this conversation, create a brief summary (2-3 sentences) that captures:
1. Main concerns or tasks discussed
2. Cognitive distortions identified
3. Progress made

Conversation:
{json.dumps(messages, indent=2)}

Provide only the summary text, no JSON."""

            chat = self.model.start_chat()
            response = chat.send_message(prompt)

            return response.text.strip()

        except Exception as e:
            print(f"Error generating summary: {e}")
            return "Session summary unavailable."
