"""
OpenAI LLM Service

Handles all interactions with OpenAI API including:
- Context window management
- Token counting and optimization
- Prompt engineering
- Response generation
"""

from openai import OpenAI
from django.conf import settings
from typing import List, Dict, Optional
import tiktoken
import logging

logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with OpenAI's language models."""
    
    def __init__(self):
        """Initialize the LLM service with API key and configuration."""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        # GPT-3.5-turbo is fastest and most cost-effective
        self.model = "gpt-3.5-turbo"
        self.max_tokens = 1500  # Reduced context for speed
        self.response_max_tokens = 250  # Shorter responses = faster
        try:
            self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        except Exception:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            Number of tokens
        """
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            # Fallback: rough estimate
            return len(text) // 4
    
    def build_system_prompt(self, user_data: Dict, memories: List[str], protocols: List[str], concise: bool = True) -> str:
        """
        Build the system prompt with user context and protocols.
        
        Args:
            user_data: Dictionary containing user information
            memories: List of relevant long-term memories
            protocols: List of relevant medical protocols
            concise: If True, use shorter prompt for faster responses
            
        Returns:
            Complete system prompt
        """
        # Always use concise mode for speed
        prompt = """You are an AI Health Coach. Be warm, friendly, and conversational like WhatsApp chat. Keep responses SHORT (2-3 sentences max). Never diagnose - suggest seeing a doctor for medical issues. Use emojis occasionally.

"""
        
        # Add comprehensive user context if available
        if user_data:
            context_parts = []
            
            # Basic info
            if user_data.get('name'):
                basic = f"{user_data.get('name')}"
                if user_data.get('age'):
                    basic += f", {user_data.get('age')}yo"
                if user_data.get('gender'):
                    basic += f", {user_data.get('gender')}"
                context_parts.append(basic)
            
            # Health background
            if user_data.get('health_conditions'):
                context_parts.append(f"Conditions: {', '.join(user_data.get('health_conditions'))}")
            if user_data.get('medications'):
                context_parts.append(f"Meds: {', '.join(user_data.get('medications'))}")
            
            # Goals & lifestyle
            if user_data.get('health_goals'):
                context_parts.append(f"Goals: {', '.join(user_data.get('health_goals'))}")
            if user_data.get('activity_level'):
                context_parts.append(f"Activity: {user_data.get('activity_level')}")
            if user_data.get('dietary_preferences'):
                context_parts.append(f"Diet: {', '.join(user_data.get('dietary_preferences'))}")
            
            if context_parts:
                prompt += "User: " + " | ".join(context_parts) + "\n"
        
        # Add only top 2 memories for speed
        if memories:
            prompt += "Remember: " + "; ".join(memories[:2]) + "\n"
        
        # Skip protocols for speed - safety is in main prompt
        
        return prompt
    
    def optimize_context(self, messages: List[Dict], max_tokens: int) -> List[Dict]:
        """
        Optimize message context to fit within token limit.
        
        Strategy:
        1. Always keep the latest messages
        2. Keep important system messages
        3. Summarize or remove older messages if needed
        
        Args:
            messages: List of message dictionaries
            max_tokens: Maximum number of tokens allowed
            
        Returns:
            Optimized list of messages
        """
        if not messages:
            return []
        
        # Calculate total tokens
        total_tokens = sum(self.count_tokens(msg['content']) for msg in messages)
        
        if total_tokens <= max_tokens:
            return messages
        
        # Keep system message if present
        system_messages = [msg for msg in messages if msg['role'] == 'system']
        other_messages = [msg for msg in messages if msg['role'] != 'system']
        
        # Always keep the latest messages
        optimized = system_messages.copy()
        tokens_used = sum(self.count_tokens(msg['content']) for msg in optimized)
        
        # Add messages from newest to oldest until we hit the limit
        for msg in reversed(other_messages):
            msg_tokens = self.count_tokens(msg['content'])
            if tokens_used + msg_tokens <= max_tokens:
                optimized.insert(len(system_messages), msg)
                tokens_used += msg_tokens
            else:
                break
        
        # If we had to cut messages, add a summary note
        if len(optimized) < len(messages):
            logger.info(f"Context optimized: {len(messages)} -> {len(optimized)} messages")
        
        return optimized
    
    def generate_response(
        self,
        messages: List[Dict],
        user_data: Optional[Dict] = None,
        memories: Optional[List[str]] = None,
        protocols: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """
        Generate a response using OpenAI API.
        
        Args:
            messages: List of conversation messages
            user_data: User profile information
            memories: Relevant long-term memories
            protocols: Relevant medical protocols
            temperature: Sampling temperature (0-2)
            
        Returns:
            Dictionary containing response and metadata
        """
        try:
            # Build system prompt
            system_prompt = self.build_system_prompt(
                user_data or {},
                memories or [],
                protocols or []
            )
            
            # Prepare messages with system prompt
            full_messages = [{"role": "system", "content": system_prompt}] + messages
            
            # Optimize context to fit token limit
            full_messages = self.optimize_context(full_messages, self.max_tokens)
            
            # Call OpenAI API
            logger.info(f"Calling OpenAI API with {len(full_messages)} messages")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=0.7,
                max_tokens=self.response_max_tokens,
            )
            
            # Extract response
            assistant_message = response.choices[0].message.content
            tokens_used = response.usage.total_tokens
            
            logger.info(f"Generated response with {tokens_used} tokens")
            
            return {
                'content': assistant_message,
                'tokens': tokens_used,
                'model': self.model,
                'finish_reason': response.choices[0].finish_reason
            }
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return {
                'content': "I'm having trouble connecting to my systems right now. Please try again in a moment.",
                'tokens': 0,
                'error': str(e)
            }
    
    def stream_response(
        self,
        messages: List[Dict],
        user_data: Optional[Dict] = None,
        memories: Optional[List[str]] = None,
        protocols: Optional[List[str]] = None,
        temperature: float = 0.7
    ):
        """
        Stream a response using OpenAI API.
        
        Yields chunks of text as they are generated.
        
        Args:
            messages: List of conversation messages
            user_data: User profile information
            memories: Relevant long-term memories
            protocols: Relevant medical protocols
            temperature: Sampling temperature (0-2)
            
        Yields:
            Text chunks as they are generated
        """
        try:
            # Build system prompt
            system_prompt = self.build_system_prompt(
                user_data or {},
                memories or [],
                protocols or []
            )
            
            # Prepare messages with system prompt
            full_messages = [{"role": "system", "content": system_prompt}] + messages
            
            # Optimize context to fit token limit
            full_messages = self.optimize_context(full_messages, self.max_tokens)
            
            # Call OpenAI API with streaming
            logger.info(f"Calling OpenAI API (streaming) with {len(full_messages)} messages")
            
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=0.7,
                max_tokens=self.response_max_tokens,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield "I apologize, but I encountered an error. Please try again."
    
    def generate_onboarding_message(self) -> str:
        """
        Generate an initial onboarding message.
        
        Returns:
            Onboarding message string
        """
        return """Hey there! 👋 I'm your personal AI Health Coach, and I'm excited to help you achieve your health goals!

Feel free to ask me anything about:
• Nutrition and meal planning 🥗
• Exercise and fitness routines 💪
• Sleep and stress management 😴
• General wellness tips 🌟
• Healthy habits and lifestyle changes 🎯

You can also add more details about your health (conditions, medications, dietary preferences) anytime, and I'll provide even more personalized advice.

What would you like to know about today? 😊"""
    
    def extract_user_info(self, message: str, existing_data: Dict) -> Dict:
        """
        Extract user information from a message using LLM.
        
        Args:
            message: User's message
            existing_data: Existing user data
            
        Returns:
            Updated user data dictionary
        """
        try:
            prompt = f"""Extract any personal health information from the following message and return it as a JSON object.
Only extract information that is explicitly stated.

Existing data: {existing_data}
New message: {message}

Extract these fields:
- name (string)
- age (number)
- gender (string)
- health_conditions (list of strings)
- medications (list of strings)
- allergies (list of strings)
- health_goals (list of strings) - e.g., "lose weight", "improve fitness", "better sleep"
- activity_level (string) - sedentary, lightly_active, moderately_active, very_active
- dietary_preferences (list of strings) - e.g., "vegetarian", "vegan", "keto"
- sleep_hours (number) - average hours per night
- sleep_issues (list of strings) - e.g., "insomnia", "snoring"
- occupation (string)
- recent_health_events (list of strings) - any recent changes or events

Return ONLY a JSON object, no other text."""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a data extraction assistant. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=500
            )
            
            import json
            extracted = json.loads(response.choices[0].message.content)
            
            # Merge with existing data
            result = existing_data.copy()
            for key, value in extracted.items():
                if value:  # Only update if value is not empty
                    if isinstance(value, list) and key in result:
                        # Merge lists without duplicates
                        result[key] = list(set(result.get(key, []) + value))
                    else:
                        result[key] = value
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting user info: {e}")
            return existing_data
