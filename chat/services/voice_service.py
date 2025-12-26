"""
Voice Service for OpenAI Whisper (STT) and TTS

Handles:
- Speech-to-text using OpenAI Whisper API
- Text-to-speech using OpenAI TTS API
- Audio file processing and streaming
"""

from openai import OpenAI
from django.conf import settings
import logging
import tempfile
import os

logger = logging.getLogger(__name__)


class VoiceService:
    """Service for handling voice input/output with OpenAI APIs."""
    
    def __init__(self):
        """Initialize the voice service with OpenAI client."""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.tts_model = "tts-1"  # Faster model for lower latency
        self.tts_voice = "nova"  # Natural female voice
        self.whisper_model = "whisper-1"
    
    def transcribe_audio(self, audio_file) -> dict:
        """
        Transcribe audio to text using Whisper API.
        
        Args:
            audio_file: Audio file object (Django UploadedFile or file-like object)
            
        Returns:
            Dictionary with transcription and metadata
        """
        try:
            logger.info("Transcribing audio with Whisper API")
            
            # Handle Django UploadedFile - need to pass as tuple with filename
            if hasattr(audio_file, 'name'):
                # Django UploadedFile - create tuple format for OpenAI
                file_tuple = (audio_file.name, audio_file.read(), audio_file.content_type)
            else:
                # Regular file object
                file_tuple = audio_file
            
            # Call Whisper API
            transcript = self.client.audio.transcriptions.create(
                model=self.whisper_model,
                file=file_tuple,
                response_format="json"
            )
            
            logger.info(f"Transcription successful: {len(transcript.text)} characters")
            
            return {
                'success': True,
                'text': transcript.text,
                'language': getattr(transcript, 'language', 'en')
            }
            
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }
    
    def generate_speech(self, text: str, speed: float = 1.0) -> bytes:
        """
        Generate speech from text using OpenAI TTS API.
        
        Args:
            text: Text to convert to speech
            speed: Speech speed (0.25 to 4.0, default 1.0)
            
        Returns:
            Audio data as bytes (MP3 format)
        """
        try:
            logger.info(f"Generating speech for {len(text)} characters")
            
            # Clean text for better TTS output
            clean_text = self._clean_text_for_tts(text)
            
            # Call TTS API with streaming for lower latency
            response = self.client.audio.speech.create(
                model=self.tts_model,
                voice=self.tts_voice,
                input=clean_text,
                speed=speed
            )
            
            # Get audio bytes
            audio_data = response.content
            
            logger.info(f"Speech generation successful: {len(audio_data)} bytes")
            
            return audio_data
            
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            raise
    
    def stream_speech(self, text: str, speed: float = 1.0):
        """
        Stream speech generation for lower latency.
        
        Args:
            text: Text to convert to speech
            speed: Speech speed (0.25 to 4.0, default 1.0)
            
        Yields:
            Audio chunks as they are generated
        """
        try:
            logger.info(f"Streaming speech for {len(text)} characters")
            
            # Clean text for better TTS output
            clean_text = self._clean_text_for_tts(text)
            
            # Call TTS API with streaming
            response = self.client.audio.speech.create(
                model=self.tts_model,
                voice=self.tts_voice,
                input=clean_text,
                speed=speed
            )
            
            # Stream the response
            yield response.content
            
        except Exception as e:
            logger.error(f"TTS streaming error: {e}")
            raise
    
    def _clean_text_for_tts(self, text: str) -> str:
        """
        Clean text for better TTS output.
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text suitable for TTS
        """
        # Remove emojis and special characters
        import re
        
        # Remove common emojis
        text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\u2600-\u26FF\u2700-\u27BF]', '', text)
        
        # Remove markdown bold
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        
        # Remove special symbols
        text = text.replace('⚠️', '').replace('✓', '').replace('•', '')
        
        # Clean up whitespace
        text = ' '.join(text.split())
        
        return text.strip()
