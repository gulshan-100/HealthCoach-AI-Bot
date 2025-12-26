"""
Chat Service

Main service coordinating all chat functionality including:
- Message handling
- User management
- Context assembly
- Response generation
"""

from chat.models import User, Message, TypingIndicator
from chat.services.llm_service import LLMService
from chat.services.memory_service import MemoryService
from chat.services.protocol_service import ProtocolService
from django.core.cache import cache
from django.utils import timezone
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ChatService:
    """Main service for chat operations."""
    
    def __init__(self):
        """Initialize all service components."""
        self.llm_service = LLMService()
        self.memory_service = MemoryService()
        self.protocol_service = ProtocolService()
    
    def get_or_create_user(self, user_id: str) -> User:
        """
        Get or create a user.
        
        Args:
            user_id: The user ID (can be session ID or device ID)
            
        Returns:
            User dict
        """
        user, created = User.get_or_create(user_id)
        
        if created:
            logger.info(f"Created new user: {user_id}")
            # Send onboarding message
            self._create_onboarding_message(user_id)
        
        return user
    
    def _create_onboarding_message(self, user_id: str):
        """Create initial onboarding message."""
        onboarding_content = self.llm_service.generate_onboarding_message()
        
        Message.create(
            user_id=user_id,
            role='assistant',
            content=onboarding_content,
            metadata={'type': 'onboarding'}
        )
    
    def get_messages(
        self,
        user_id: str,
        limit: int = 50,
        before_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get messages for a user with pagination.
        
        Args:
            user_id: The user ID
            limit: Maximum number of messages to return
            before_id: Get messages before this message ID (for pagination)
            
        Returns:
            List of message dictionaries
        """
        query = {'user_id': user_id}
        
        if before_id:
            messages = Message.get_messages(user_id, limit, before_id)
        else:
            messages = Message.get_messages(user_id, limit)
        
        messages.reverse()  # Return in chronological order
        
        return [
            {
                'message_id': str(msg['message_id']),
                'role': msg['role'],
                'content': msg['content'],
                'created_at': msg['created_at'].isoformat(),
                'metadata': msg.get('metadata', {})
            }
            for msg in messages
        ]
    
    def get_recent_context(self, user_id: str, limit: int = 10) -> List[Dict]:
        """
        Get recent messages for LLM context.
        
        Args:
            user_id: The user ID
            limit: Number of recent messages
            
        Returns:
            List of message dictionaries for LLM
        """
        messages = Message.get_messages(user_id, limit)
        
        # Reverse to get chronological order
        messages = list(reversed(messages))
        
        return [
            {'role': msg['role'], 'content': msg['content']}
            for msg in messages
            if msg['role'] in ['user', 'assistant']  # Exclude system messages
        ]
    
    def send_message(self, user_id: str, content: str) -> Dict:
        """
        Process a user message and generate response.
        
        Args:
            user_id: The user ID
            content: The message content
            
        Returns:
            Dictionary with user message and assistant response
        """
        try:
            # Validate input
            if not content or not content.strip():
                raise ValueError("Message content cannot be empty")
            
            if len(content) > 2000:
                raise ValueError("Message is too long (max 2000 characters)")
            
            # Get or create user
            user = self.get_or_create_user(user_id)
            
            # Save user message
            user_message = Message.create(
                user_id=user_id,
                role='user',
                content=content.strip(),
                tokens=self.llm_service.count_tokens(content)
            )
            
            # Set typing indicator
            self.set_typing_indicator(user_id, True)
            
            # Extract user info if onboarding not completed
            if not user.get('onboarding_completed'):
                user_data = self.llm_service.extract_user_info(
                    content,
                    {
                        'name': user.get('name'),
                        'age': user.get('age'),
                        'gender': user.get('gender'),
                        'health_conditions': user.get('health_conditions', []),
                        'medications': user.get('medications', []),
                        'allergies': user.get('allergies', [])
                    }
                )
                
                # Update user if new info found
                update_data = {}
                for key, value in user_data.items():
                    if value and user.get(key) != value:
                        update_data[key] = value
                
                if update_data:
                    User.update(user_id, **update_data)
                    user = User.get(user_id)  # Refresh user data
                
                # Mark onboarding complete if basic info collected
                if user.get('name') and user.get('age'):
                    User.update(user_id, onboarding_completed=True)
                    logger.info(f"Onboarding completed for user {user_id}")
            
            # Get recent conversation context (minimal for speed)
            recent_messages = self.get_recent_context(user_id, limit=6)
            
            # Get relevant memories (limited for speed)
            memories = self.memory_service.get_relevant_memories(user_id, content)[:3]
            
            # Skip protocol matching for speed - safety is in system prompt
            protocols = []
            
            # Prepare user data
            user_data = {
                'name': user.get('name'),
                'age': user.get('age'),
                'gender': user.get('gender'),
                'health_conditions': user.get('health_conditions', []),
                'medications': user.get('medications', []),
                'allergies': user.get('allergies', [])
            }
            
            # Generate response
            response = self.llm_service.generate_response(
                messages=recent_messages,
                user_data=user_data,
                memories=memories,
                protocols=protocols
            )
            
            # Save assistant message
            assistant_message = Message.create(
                user_id=user_id,
                role='assistant',
                content=response['content'],
                tokens=response.get('tokens', 0),
                metadata={
                    'model': response.get('model', ''),
                    'finish_reason': response.get('finish_reason', '')
                }
            )
            
            # Clear typing indicator
            self.set_typing_indicator(user_id, False)
            
            # Extract memories periodically (every 5 messages)
            # This stores long-term user context for personalization
            message_count = Message.count(user_id)
            if message_count > 0 and message_count % 5 == 0:
                try:
                    self.memory_service.extract_memories_from_conversation(
                        user_id,
                        recent_messages[-5:],
                        self.llm_service
                    )
                except Exception as e:
                    logger.warning(f"Memory extraction skipped: {e}")
            
            return {
                'user_message': {
                    'message_id': str(user_message['message_id']),
                    'role': 'user',
                    'content': user_message['content'],
                    'created_at': user_message['created_at'].isoformat()
                },
                'assistant_message': {
                    'message_id': str(assistant_message['message_id']),
                    'role': 'assistant',
                    'content': assistant_message['content'],
                    'created_at': assistant_message['created_at'].isoformat()
                }
            }
            
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            # Clear typing indicator on error
            self.set_typing_indicator(user_id, False)
            raise
    
    def set_typing_indicator(self, user_id: str, is_typing: bool):
        """
        Set typing indicator status.
        
        Args:
            user_id: The user ID
            is_typing: Whether assistant is typing
        """
        try:
            TypingIndicator.set_typing(user_id, is_typing)
            
            # Also cache for quick access
            cache.set(f"typing:{user_id}", is_typing, 30)
            
        except Exception as e:
            logger.error(f"Error setting typing indicator: {e}")
    
    def get_typing_indicator(self, user_id: str) -> bool:
        """
        Get typing indicator status.
        
        Args:
            user_id: The user ID
            
        Returns:
            True if assistant is typing, False otherwise
        """
        # Try cache first
        cached = cache.get(f"typing:{user_id}")
        if cached is not None:
            return cached
        
        # Fall back to database
        try:
            indicator = TypingIndicator.get_status(user_id)
            return indicator
        except Exception:
            return False
    
    def get_user_profile(self, user_id: str) -> Dict:
        """
        Get user profile.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dictionary with user profile
        """
        try:
            user = User.get(user_id)
            if not user:
                return None
                
            return {
                'user_id': user['user_id'],
                'name': user.get('name'),
                'age': user.get('age'),
                'gender': user.get('gender'),
                'health_conditions': user.get('health_conditions', []),
                'medications': user.get('medications', []),
                'allergies': user.get('allergies', []),
                'onboarding_completed': user.get('onboarding_completed', False),
                'created_at': user['created_at'].isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return None
