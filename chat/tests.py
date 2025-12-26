"""
Tests for Chat Service
"""

from django.test import TestCase
from chat.models import User, Message, Memory, Protocol
from chat.services.chat_service import ChatService


class ChatServiceTests(TestCase):
    """Test cases for ChatService"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.chat_service = ChatService()
        self.test_user_id = "test_user_123"
    
    def test_get_or_create_user(self):
        """Test user creation"""
        user = self.chat_service.get_or_create_user(self.test_user_id)
        self.assertIsNotNone(user)
        self.assertEqual(user.user_id, self.test_user_id)
        self.assertFalse(user.onboarding_completed)
    
    def test_get_messages(self):
        """Test message retrieval"""
        user = self.chat_service.get_or_create_user(self.test_user_id)
        messages = self.chat_service.get_messages(self.test_user_id)
        self.assertIsInstance(messages, list)
    
    # Add more tests as needed
