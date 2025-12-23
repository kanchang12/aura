from elevenlabs import ElevenLabs, VoiceSettings
from config import Config
import os

class ElevenLabsService:
    """ElevenLabs service for voice interaction"""

    def __init__(self):
        self.client = ElevenLabs(api_key=Config.ELEVENLABS_API_KEY)
        self.agent_id = Config.ELEVENLABS_AGENT_ID

    def text_to_speech(self, text, voice_id="pNInz6obpgDQGcFmaJgB"):  # Adam voice
        """
        Convert text to speech using ElevenLabs

        Args:
            text: Text to convert to speech
            voice_id: ElevenLabs voice ID (default: Adam - friendly male voice)

        Returns:
            bytes: Audio data
        """
        try:
            audio = self.client.text_to_speech.convert(
                voice_id=voice_id,
                text=text,
                model_id="eleven_turbo_v2_5",
                voice_settings=VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.75,
                    style=0.5,
                    use_speaker_boost=True
                )
            )

            # Convert generator to bytes
            audio_bytes = b""
            for chunk in audio:
                audio_bytes += chunk

            return audio_bytes

        except Exception as e:
            print(f"Error in text-to-speech: {e}")
            return None

    def create_conversational_agent(self, cbt_prompt, knowledge_base):
        """
        Create an ElevenLabs Conversational Agent with CBT prompt

        This method configures an ElevenLabs agent with the CBT coaching prompt
        and knowledge base for natural voice conversations.

        Args:
            cbt_prompt: The CBT coaching system prompt
            knowledge_base: JSON knowledge base for CBT techniques

        Returns:
            dict: Agent configuration
        """
        try:
            # Note: This is a placeholder for ElevenLabs Conversational AI API
            # The actual implementation will depend on ElevenLabs' agent API structure

            agent_config = {
                "agent_id": self.agent_id,
                "prompt": cbt_prompt,
                "knowledge_base": knowledge_base,
                "voice_settings": {
                    "voice_id": "pNInz6obpgDQGcFmaJgB",  # Friendly male voice
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.5
                },
                "conversation_config": {
                    "max_duration_seconds": 3600,  # 1 hour max
                    "interruption_threshold": 100,
                    "response_delay_ms": 500
                }
            }

            return agent_config

        except Exception as e:
            print(f"Error creating conversational agent: {e}")
            return None

    def start_conversation(self, user_id, session_id):
        """
        Start a conversational AI session

        Args:
            user_id: User ID
            session_id: Session ID

        Returns:
            dict: Conversation session info
        """
        try:
            # This would integrate with ElevenLabs Conversational AI SDK
            # For now, return session configuration

            return {
                "session_id": session_id,
                "user_id": user_id,
                "agent_id": self.agent_id,
                "status": "active",
                "websocket_url": f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={self.agent_id}"
            }

        except Exception as e:
            print(f"Error starting conversation: {e}")
            return None

    def process_voice_input(self, audio_data):
        """
        Process voice input and return transcription

        Args:
            audio_data: Audio bytes

        Returns:
            str: Transcribed text
        """
        try:
            # Use ElevenLabs speech-to-text if available
            # Otherwise, integrate with Google Speech-to-Text

            # Placeholder - actual implementation depends on ElevenLabs API
            return "[Transcription would be here]"

        except Exception as e:
            print(f"Error processing voice input: {e}")
            return None
